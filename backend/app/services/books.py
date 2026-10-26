"""Large book files: storage paths, disk-space guard, background PDF text extraction, cleanup."""
import asyncio
import hashlib
import json
import logging
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import config
from ..database import SessionLocal
from ..models import Book, BookPage, UploadSession

log = logging.getLogger(__name__)

PDF_MAGIC = b"%PDF-"
EXTRACT_WINDOW = 200                   # pages per worker process / DB transaction
_extract_lock = asyncio.Semaphore(1)   # one book at a time keeps memory and CPU flat


def books_dir() -> Path:
    d = config.UPLOAD_DIR / "books"
    d.mkdir(parents=True, exist_ok=True)
    return d


def tmp_dir() -> Path:
    d = config.UPLOAD_DIR / "tmp"
    d.mkdir(parents=True, exist_ok=True)
    return d


def part_path(upload_id: str) -> Path:
    return tmp_dir() / f"{upload_id}.part"


def book_path(book: Book) -> Path:
    return books_dir() / book.file_name


def has_room(extra_bytes: int) -> bool:
    """True if writing extra_bytes still leaves DISK_RESERVE_MB free on the upload volume."""
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(config.UPLOAD_DIR).free
    return free - extra_bytes > config.DISK_RESERVE_MB * 1024 * 1024


def storage_stats() -> dict:
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(config.UPLOAD_DIR)

    def size_of(p: Path) -> int:
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.exists() else 0

    return {
        "total": usage.total, "free": usage.free,
        "books": size_of(config.UPLOAD_DIR / "books"),
        "images": sum(f.stat().st_size for f in config.UPLOAD_DIR.glob("*") if f.is_file()),
        "pending_uploads": size_of(config.UPLOAD_DIR / "tmp"),
    }


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def looks_like_pdf(path: Path) -> bool:
    with path.open("rb") as f:
        head = f.read(1024)
    # The header may be preceded by a few junk bytes; the spec allows it within the first 1 KB.
    return PDF_MAGIC in head


# ---------------------------------------------------------------- text extraction

def _limit_memory() -> None:  # runs in the child before exec
    try:
        import resource

        cap = config.PDF_WORKER_MEM_MB * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
    except (ImportError, ValueError, OSError):
        pass


async def _worker(*args: str) -> list[str]:
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "app.services.pdftext", *args,
        cwd=str(config.BASE_DIR), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        preexec_fn=_limit_memory if os.name == "posix" else None,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=config.PDF_WORKER_TIMEOUT_S)
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError("pdf worker timed out")
    if proc.returncode != 0:
        raise RuntimeError(f"pdf worker failed ({proc.returncode}): {err.decode(errors='replace')[-300:]}")
    return out.decode("utf-8").splitlines()


async def _set_status(book_id: int, **fields) -> None:
    async with SessionLocal() as s:
        book = await s.get(Book, book_id)
        if book:
            for k, v in fields.items():
                setattr(book, k, v)
            await s.commit()


async def extract_text(book_id: int) -> None:
    """Extract page text window by window, each window in its own memory-capped subprocess."""
    async with _extract_lock:
        async with SessionLocal() as s:
            book = await s.get(Book, book_id)
            if not book or not book.file_name:
                return
            path = str(book_path(book))
            await s.execute(delete(BookPage).where(BookPage.book_id == book_id))
            book.text_status, book.text_pages_done = "processing", 0
            await s.commit()
        try:
            # Make the file open fast in pdf.js (see pdftext.optimize_for_web), then index it.
            result = json.loads((await _worker("optimize", path))[0])
            log.info("book %s web optimisation: %s", book_id, result)
            await _set_status(book_id, file_size=Path(path).stat().st_size)
            total = int((await _worker("count", path))[0])
            await _set_status(book_id, pages=total)
            for start in range(0, total, EXTRACT_WINDOW):
                lines = await _worker("extract", path, str(start), str(start + EXTRACT_WINDOW))
                rows = [json.loads(line) for line in lines if line]
                async with SessionLocal() as s:
                    book = await s.get(Book, book_id)
                    if book is None:  # deleted while we were working
                        return
                    s.add_all(BookPage(book_id=book_id, page=r["page"], text=r["text"]) for r in rows)
                    book.text_pages_done = min(total, start + EXTRACT_WINDOW)
                    await s.commit()
            await _set_status(book_id, text_status="ready")
        except Exception:
            log.exception("text extraction failed for book %s", book_id)
            await _set_status(book_id, text_status="failed")


def schedule_extraction(book_id: int) -> None:
    asyncio.get_running_loop().create_task(extract_text(book_id))


async def resume_pending_extractions() -> None:
    """Called on startup: finish books whose extraction was interrupted by a restart."""
    async with SessionLocal() as s:
        ids = (await s.execute(
            select(Book.id).where(Book.text_status.in_(["queued", "processing"]))
        )).scalars().all()
    for book_id in ids:
        schedule_extraction(book_id)


async def purge_stale_uploads(session: AsyncSession) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=config.UPLOAD_TTL_HOURS)
    stale = (await session.execute(select(UploadSession).where(UploadSession.updated_at < cutoff))).scalars().all()
    for up in stale:
        part_path(up.id).unlink(missing_ok=True)
        await session.delete(up)
    await session.commit()
    return len(stale)
