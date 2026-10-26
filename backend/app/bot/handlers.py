"""Incoming bot updates: launcher, web login links, inline panel approval."""
import html
import secrets
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, MenuButtonWebApp, Message, WebAppInfo
from sqlalchemy import select

from .. import config
from ..database import SessionLocal
from ..models import IgxMarker, LoginToken, Role, User
from ..routers.auth import upsert_telegram_user
from ..services import biopsy as workflow
from ..services.inventory import InsufficientStock, status_tags
from . import notify
from .texts import t

router = Router()


def _tg_dict(u) -> dict:
    return {"id": u.id, "first_name": u.first_name, "last_name": u.last_name,
            "username": u.username, "language_code": u.language_code}


@router.message(CommandStart())
async def start(message: Message):
    async with SessionLocal() as session:
        user = await upsert_telegram_user(session, _tg_dict(message.from_user))
        await session.commit()
    lang = user.language
    await message.answer(
        t(lang, "welcome", name=html.escape(user.name), role=t(lang, "roles")[user.role]) + "\n\n" + t(lang, "help"),
        reply_markup=notify.keyboard([notify.webapp_button(t(lang, "open_app"))]),
        parse_mode="HTML",
    )


@router.message(Command("login"))
async def login(message: Message):
    async with SessionLocal() as session:
        user = await upsert_telegram_user(session, _tg_dict(message.from_user))
        if not config.WEBAPP_URL:
            await session.commit()
            return await message.answer(t(user.language, "login_no_url"))
        token = secrets.token_urlsafe(32)
        session.add(LoginToken(token=token, user_id=user.id,
                               expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)))
        await session.commit()
    await message.answer(t(user.language, "login_link", url=f"{config.WEBAPP_URL}/#/login?token={token}"),
                         disable_web_page_preview=True)


@router.message(Command("til"))
async def toggle_language(message: Message):
    async with SessionLocal() as session:
        user = await upsert_telegram_user(session, _tg_dict(message.from_user))
        user.language = "ru" if user.language == "uz" else "uz"
        await session.commit()
    await message.answer(t(user.language, "lang_set"))


@router.message(Command("inventar", "inventory"))
async def inventory(message: Message):
    async with SessionLocal() as session:
        user = await upsert_telegram_user(session, _tg_dict(message.from_user))
        await session.commit()
        if user.role == Role.RESIDENT:
            return await message.answer(t(user.language, "forbidden"))
        counts = {"total": 0, "expiring": 0, "slow": 0, "fast": 0, "low_stock": 0, "out_of_stock": 0}
        for m in (await session.execute(select(IgxMarker))).scalars():
            counts["total"] += 1
            for tag in status_tags(m):
                counts[tag] += 1
    await message.answer(t(user.language, "inventory", **counts), parse_mode="HTML",
                         reply_markup=notify.keyboard([notify.webapp_button(t(user.language, "open_app"), "#/inventory")]))


@router.callback_query(F.data.startswith("approve:"))
async def approve(cb: CallbackQuery):
    code = cb.data.split(":", 1)[1]
    async with SessionLocal() as session:
        user = (await session.execute(select(User).where(User.telegram_id == cb.from_user.id))).scalar()
        lang = user.language if user else "uz"
        if not user or not user.is_active or user.role not in (Role.PATHOLOGIST, Role.SUPER_ADMIN):
            return await cb.answer(t(lang, "forbidden"), show_alert=True)
        try:
            _, report = await workflow.approve(session, code, user)
            await session.commit()
        except LookupError:
            return await cb.answer(t(lang, "not_found"), show_alert=True)
        except workflow.WorkflowError as e:
            key = "no_markers" if "No markers" in str(e) else "already"
            await cb.answer()
            return await cb.message.edit_text(t(lang, key, code=code), parse_mode="HTML")
        except InsufficientStock as e:
            await session.rollback()
            await cb.answer()
            await notify.shortage(code, e.names)
            return await cb.message.answer(t(lang, "shortage", code=code, markers=html.escape(", ".join(e.names))),
                                           parse_mode="HTML")
    items = ", ".join(f"{r['name']} ({r['stock_left']})" for r in report)
    await cb.answer("✅")
    await cb.message.edit_text(t(lang, "approved", code=code, by=html.escape(user.name), items=html.escape(items)),
                               parse_mode="HTML")
    await notify.low_stock_after([r["name"] for r in report])


def create_bot() -> tuple[Bot, Dispatcher]:
    bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    dp.include_router(router)
    return bot, dp


async def setup_menu(bot: Bot) -> None:
    if config.WEBAPP_URL.startswith("https://"):
        await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="PathoUz", web_app=WebAppInfo(url=config.WEBAPP_URL)))
