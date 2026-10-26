"""PathoUz entry point: FastAPI API + built React frontend + Telegram bot in one process.

    uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
import asyncio
import contextlib
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config, database, seed
from .bot import notify
from .routers import academy, admin, atlas, auth, biopsies, images, inventory, search, uploads
from .services import books
from .services.inventory import refresh_all

log = logging.getLogger("pathouz")
TZ = ZoneInfo(os.getenv("TZ_NAME", "Asia/Tashkent"))
DIGEST_HOUR = int(os.getenv("DIGEST_HOUR", "8"))


async def _daily_jobs() -> None:
    """Every morning: recompute 30-day usage windows and send the expiry digest."""
    while True:
        now = datetime.now(TZ)
        nxt = now.replace(hour=DIGEST_HOUR, minute=0, second=0, microsecond=0)
        if nxt <= now:
            nxt += timedelta(days=1)
        await asyncio.sleep((nxt - now).total_seconds())
        try:
            async with database.SessionLocal() as session:
                await refresh_all(session)
                await session.commit()
                await books.purge_stale_uploads(session)
            await notify.expiry_digest()
        except Exception:
            log.exception("daily job failed")


async def _start_bot() -> asyncio.Task | None:
    if not (config.BOT_TOKEN and config.RUN_BOT):
        log.warning("BOT_TOKEN not set — Telegram bot disabled")
        return None
    from .bot.handlers import create_bot, setup_menu

    bot, dp = create_bot()
    notify.bot = bot
    try:
        await setup_menu(bot)
    except Exception:
        log.exception("could not set menu button")
    return asyncio.create_task(dp.start_polling(bot, handle_signals=False))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    await database.migrate()
    if config.SEED_ON_START:
        async with database.SessionLocal() as session:
            await seed.run(session, demo=os.getenv("SEED_DEMO", "0") == "1")
    async with database.SessionLocal() as session:
        await refresh_all(session)
        await session.commit()
    await books.resume_pending_extractions()
    tasks = [t for t in (await _start_bot(), asyncio.create_task(_daily_jobs())) if t]
    yield
    for t in tasks:
        t.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await t
    if notify.bot:
        await notify.bot.session.close()
        notify.bot = None


class SecurityHeaders:
    """Pure ASGI middleware (does not buffer bodies, so streaming uploads/downloads stay streaming)."""

    # Telegram Web (web.telegram.org) shows Mini Apps in an iframe, so framing is allowed only there.
    FRAME = b"frame-ancestors 'self' https://web.telegram.org https://*.telegram.org"
    # Uploaded SVG/PDF must never run scripts in our origin, even if opened directly.
    FILES = b"default-src 'none'; style-src 'unsafe-inline'; sandbox"
    # Printable pages: inline CSS and the one-line print button only, no external loads.
    PRINT = b"default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; frame-ancestors 'none'"

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope["path"]
        is_file = path.startswith("/api/images/") or (path.startswith("/api/books/") and path.endswith("/file"))
        is_print = path.startswith("/api/print/")

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = [(k, v) for k, v in message.get("headers", []) if k.lower() != b"content-security-policy"]
                headers += [(b"x-content-type-options", b"nosniff"),
                            (b"referrer-policy", b"strict-origin-when-cross-origin"),
                            (b"content-security-policy", self.FILES if is_file else self.PRINT if is_print else self.FRAME)]
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)


def create_app() -> FastAPI:
    app = FastAPI(title="PathoUz API", version="6.0", lifespan=lifespan,
                  docs_url="/api/docs", openapi_url="/api/openapi.json")
    for r in (auth, admin, inventory, biopsies, images, atlas, academy, search, uploads):
        app.include_router(r.router)
    app.include_router(biopsies.print_router)

    app.add_middleware(SecurityHeaders)

    @app.get("/api/health", include_in_schema=False)
    async def health():
        return {"ok": True, "dev": config.DEV_MODE, "bot": bool(config.BOT_TOKEN), "bot_username": config.BOT_USERNAME,
                "max_book_mb": config.MAX_BOOK_MB}

    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
    async def api_not_found(path: str):
        return JSONResponse({"detail": "Not found"}, status_code=404)

    dist = config.FRONTEND_DIST
    if (dist / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        async def spa(path: str):
            file = (dist / path).resolve()
            if path and file.is_file() and dist.resolve() in file.parents:
                return FileResponse(file)
            return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})

    return app


app = create_app()
