"""Large-book pipeline: chunked resumable upload, PDF validation, Range streaming, text extraction."""
import asyncio
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app import config
from app.models import Biopsy, Role, User

pytestmark = pytest.mark.asyncio


def make_pdf(pages: list[str]) -> bytes:
    """Build a small, valid multi-page PDF with real text objects (no external tools)."""
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", None,
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for text in pages:
        stream = f"BT /F1 14 Tf 72 720 Td ({text}) Tj ET".encode()
        objs.append(f"<< /Length {len(stream)} >>\nstream\n{stream.decode()}\nendstream")
        content_id = len(objs)
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                    f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>")
        kids.append(f"{len(objs)} 0 R")
    objs[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>"
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{body}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets).encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


async def upload(client, h, data: bytes, name="book.pdf", chunk=None):
    up = (await client.post("/api/uploads", json={"filename": name, "size": len(data)}, headers=h)).json()
    step = chunk or up["chunk_size"]
    for off in range(0, len(data), step):
        r = await client.put(f"/api/uploads/{up['id']}?offset={off}", content=data[off:off + step], headers=h)
        assert r.status_code == 200, r.text
    return up["id"]


async def wait_ready(client, h, book_id, timeout=10):
    for _ in range(timeout * 20):
        b = next(x for x in (await client.get("/api/books", headers=h)).json() if x["id"] == book_id)
        if b["text_status"] in ("ready", "failed"):
            return b
        await asyncio.sleep(0.05)
    raise AssertionError("extraction did not finish")


async def test_chunked_resumable_upload_and_reading(client, make_user):
    _, adm = await make_user(Role.SUPER_ADMIN)
    _, res = await make_user(Role.RESIDENT)
    pdf = make_pdf(["Introduction to pathology", "HER2 scoring by ASCO CAP", "GATA3 in breast carcinoma"])
    assert (await client.post("/api/uploads", json={"filename": "x.pdf", "size": 10}, headers=res)).status_code == 403

    up = (await client.post("/api/uploads", json={"filename": "big.pdf", "size": len(pdf)}, headers=adm)).json()
    half = len(pdf) // 2
    assert (await client.put(f"/api/uploads/{up['id']}?offset=0", content=pdf[:half], headers=adm)).json()["received"] == half
    # Client lost track (e.g. app reopened): server tells it where to resume
    r = await client.put(f"/api/uploads/{up['id']}?offset=0", content=pdf[:half], headers=adm)
    assert r.status_code == 409 and r.json()["detail"]["received"] == half
    assert (await client.get(f"/api/uploads/{up['id']}", headers=adm)).json()["received"] == half
    # Finishing too early is refused
    meta = {"upload_id": up["id"], "title": "Own notes", "license": "CC BY 4.0"}
    assert (await client.post("/api/books/from-upload", json=meta, headers=adm)).status_code == 409
    # A chunk larger than what is left is rejected and does not corrupt the file
    r = await client.put(f"/api/uploads/{up['id']}?offset={half}", content=pdf[half:] + b"extra", headers=adm)
    assert r.status_code == 413
    assert (await client.get(f"/api/uploads/{up['id']}", headers=adm)).json()["received"] == half
    await client.put(f"/api/uploads/{up['id']}?offset={half}", content=pdf[half:], headers=adm)

    book = (await client.post("/api/books/from-upload", json=meta, headers=adm)).json()
    assert book["has_file"] and book["file_size"] == len(pdf)
    assert not (config.UPLOAD_DIR / "tmp" / f"{up['id']}.part").exists()

    done = await wait_ready(client, adm, book["id"])
    assert done["text_status"] == "ready" and done["pages"] == 3 and done["text_pages_done"] == 3

    hits = (await client.get(f"/api/books/{book['id']}/search?q=gata3", headers=res)).json()
    assert [x["page"] for x in hits] == [3] and "GATA3" in hits[0]["snippet"]

    # Range requests: the viewer fetches only the bytes it needs
    r = await client.get(book["file_url"], headers={**res, "Range": "bytes=0-99"})
    assert r.status_code == 206 and len(r.content) == 100 and r.content.startswith(b"%PDF")
    assert r.headers["accept-ranges"] == "bytes"
    assert "sandbox" in r.headers["content-security-policy"]
    full = await client.get(book["file_url"], headers=res)
    assert full.content == pdf

    await client.put(f"/api/books/{book['id']}/progress", json={"page": 2}, headers=res)
    assert next(b for b in (await client.get("/api/books", headers=res)).json() if b["id"] == book["id"])["progress_page"] == 2

    # Same file again -> duplicate
    again = await upload(client, adm, pdf)
    r = await client.post("/api/books/from-upload", json={**meta, "upload_id": again}, headers=adm)
    assert r.status_code == 409 and r.json()["detail"]["book_id"] == book["id"]

    path = config.UPLOAD_DIR / "books"
    assert len(list(path.glob("*.pdf"))) == 1
    assert (await client.delete(f"/api/books/{book['id']}", headers=adm)).status_code == 204
    assert list(path.glob("*.pdf")) == []


async def test_upload_rejects_non_pdf_oversize_and_full_disk(client, make_user, monkeypatch):
    _, adm = await make_user(Role.SUPER_ADMIN)
    uid = await upload(client, adm, b"PK\x03\x04 this is a zip, not a pdf" * 10)
    r = await client.post("/api/books/from-upload", json={"upload_id": uid, "title": "x", "license": "y"}, headers=adm)
    assert r.status_code == 415

    monkeypatch.setattr(config, "MAX_BOOK_MB", 1)
    assert (await client.post("/api/uploads", json={"filename": "a.pdf", "size": 2 * 1024 * 1024}, headers=adm)).status_code == 413
    monkeypatch.setattr(config, "MAX_BOOK_MB", 2048)
    monkeypatch.setattr(config, "DISK_RESERVE_MB", 10**9)
    assert (await client.post("/api/uploads", json={"filename": "a.pdf", "size": 100}, headers=adm)).status_code == 507


async def test_cancel_and_purge_uploads(client, make_user, seeded, monkeypatch):
    from app.services import books

    _, adm = await make_user(Role.SUPER_ADMIN)
    up = (await client.post("/api/uploads", json={"filename": "a.pdf", "size": 100}, headers=adm)).json()
    assert (await client.delete(f"/api/uploads/{up['id']}", headers=adm)).status_code == 204
    assert not books.part_path(up["id"]).exists()

    up = (await client.post("/api/uploads", json={"filename": "b.pdf", "size": 100}, headers=adm)).json()
    monkeypatch.setattr(config, "UPLOAD_TTL_HOURS", -1)
    async with seeded.SessionLocal() as s:
        assert await books.purge_stale_uploads(s) == 1
    assert not books.part_path(up["id"]).exists()


async def test_storage_quiz_and_headers(client, make_user):
    _, adm = await make_user(Role.SUPER_ADMIN)
    _, path = await make_user(Role.PATHOLOGIST)
    st = (await client.get("/api/storage", headers=adm)).json()
    assert st["free"] > 0 and st["max_book_mb"] == config.MAX_BOOK_MB
    assert (await client.get("/api/storage", headers=path)).status_code == 403

    q = {"case_text": {"uz": "Savol", "ru": "Вопрос"}, "options": [{"uz": "A"}, {"uz": "B"}], "correct": 1}
    assert (await client.post("/api/quiz", json={**q, "correct": 5}, headers=path)).status_code == 422
    assert (await client.post("/api/quiz", json=q, headers=path)).status_code == 201

    r = await client.get("/api/atlas/organs", headers=path)
    assert "frame-ancestors" in r.headers["content-security-policy"] and r.headers["x-content-type-options"] == "nosniff"


# ---------------------------------------------------------------- Telegram bot handler

class FakeMessage:
    def __init__(self):
        self.edited, self.sent = [], []

    async def edit_text(self, text, **kw):
        self.edited.append(text)

    async def answer(self, text, **kw):
        self.sent.append(text)


class FakeCallback:
    def __init__(self, data, tg_id):
        self.data, self.from_user, self.message, self.alerts = data, SimpleNamespace(id=tg_id), FakeMessage(), []

    async def answer(self, text=None, show_alert=False):
        self.alerts.append(text)


async def test_bot_inline_approval(client, make_user, seeded):
    from app.bot import handlers

    doctor, h = await make_user(Role.PATHOLOGIST)
    resident, _ = await make_user(Role.RESIDENT)
    code = (await client.post("/api/biopsies", headers=h, json={
        "patient_name": "Test Bemor", "organ": "breast", "selected_markers": [{"name": "ER"}]})).json()["code"]

    cb = FakeCallback(f"approve:{code}", resident.telegram_id)
    await handlers.approve(cb)
    assert cb.alerts and "⛔" in cb.alerts[0]

    cb = FakeCallback(f"approve:{code}", doctor.telegram_id)
    await handlers.approve(cb)
    assert code in cb.message.edited[0] and "ER" in cb.message.edited[0]
    async with seeded.SessionLocal() as s:
        assert (await s.execute(select(Biopsy.status).where(Biopsy.code == code))).scalar() == "approved"

    cb = FakeCallback(f"approve:{code}", doctor.telegram_id)
    await handlers.approve(cb)  # second press: already approved, no double deduction
    assert "ℹ️" in cb.message.edited[0]


# ---------------------------------------------------------------- migrations

async def test_migrations_match_models(db_url, tmp_path):
    """alembic upgrade head must produce exactly the schema the models describe."""
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from sqlalchemy.ext.asyncio import create_async_engine

    from app import database
    from app.database import Base

    url = db_url if db_url.startswith("postgresql") else f"sqlite+aiosqlite:///{tmp_path / 'mig.db'}"
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
        await conn.run_sync(database._upgrade)
        diff = await conn.run_sync(lambda c: compare_metadata(MigrationContext.configure(c), Base.metadata))
        await conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    await engine.dispose()
    assert diff == []


async def test_print_report_and_labels(client, make_user):
    _, path = await make_user(Role.PATHOLOGIST)
    _, tech = await make_user(Role.TECHNICIAN)
    code = (await client.post("/api/biopsies", headers=path, json={
        "patient_name": "<script>x</script> Ali", "organ": "breast",
        "selected_markers": [{"name": "ER"}, {"name": "GATA3"}]})).json()["code"]
    link = (await client.post(f"/api/biopsies/{code}/print-link", json={"kind": "report", "lang": "ru"}, headers=path)).json()["url"]
    page = await client.get(link)
    assert page.status_code == 200 and code in page.text and "Патогистологическое" in page.text
    assert "<script>x</script>" not in page.text and "&lt;script&gt;" in page.text
    assert "ЧЕРНОВИК" in page.text
    # token is bound to the case and kind
    assert (await client.get(link.replace("/report/", "/labels/"))).status_code == 401
    assert (await client.get(link + "x")).status_code == 401
    # technicians may print labels but not the clinical report
    assert (await client.post(f"/api/biopsies/{code}/print-link", json={"kind": "report"}, headers=tech)).status_code == 403
    labels = (await client.post(f"/api/biopsies/{code}/print-link", json={"kind": "labels"}, headers=tech)).json()["url"]
    html = (await client.get(labels)).text
    assert html.count("class='label'") == 3 and "GATA3" in html


async def test_large_book_is_web_optimized(client, make_user):
    """Books with many pages get an incremental update so pdf.js needs only the file tail to open them."""
    from io import BytesIO

    from pypdf import PdfReader

    _, adm = await make_user(Role.SUPER_ADMIN)
    pdf = make_pdf([f"Chapter page {i}" for i in range(1, 81)])
    uid = await upload(client, adm, pdf, chunk=4096)
    book = (await client.post("/api/books/from-upload", json={"upload_id": uid, "title": "Long", "license": "own"}, headers=adm)).json()
    done = await wait_ready(client, adm, book["id"])
    assert done["text_status"] == "ready" and done["pages"] == 80
    assert done["file_size"] > len(pdf)                         # incremental update appended
    data = (await client.get(book["file_url"], headers=adm)).content
    assert data[:len(pdf)] == pdf                               # original bytes untouched
    reader = PdfReader(BytesIO(data), strict=True)
    assert len(reader.pages) == 80 and "page 80" in reader.pages[79].extract_text()
    assert b"/PathoUzWeb true" in data[-4096:]
    hits = (await client.get(f"/api/books/{book['id']}/search?q=page 77", headers=adm)).json()
    assert [h["page"] for h in hits] == [77]


async def test_chunk_checksum_and_no_holes(client, make_user):
    import hashlib

    from app.services import books

    _, adm = await make_user(Role.SUPER_ADMIN)
    pdf = make_pdf(["a", "b", "c"])
    up = (await client.post("/api/uploads", json={"filename": "c.pdf", "size": len(pdf)}, headers=adm)).json()
    first, rest = pdf[:200], pdf[200:]
    good = hashlib.sha256(first).hexdigest()
    bad = await client.put(f"/api/uploads/{up['id']}?offset=0", content=first, headers={**adm, "X-Chunk-SHA256": "0" * 64})
    assert bad.status_code == 422
    assert (await client.get(f"/api/uploads/{up['id']}", headers=adm)).json()["received"] == 0
    assert books.part_path(up["id"]).stat().st_size == 0           # damaged chunk was not kept
    ok = await client.put(f"/api/uploads/{up['id']}?offset=0", content=first, headers={**adm, "X-Chunk-SHA256": good})
    assert ok.json()["received"] == 200

    # If bytes on disk went missing, the server refuses to write past them (no zero-filled holes)
    with books.part_path(up["id"]).open("r+b") as f:
        f.truncate(100)
    r = await client.put(f"/api/uploads/{up['id']}?offset=200", content=rest, headers=adm)
    assert r.status_code == 409 and r.json()["detail"]["received"] == 100
    assert (await client.get(f"/api/uploads/{up['id']}", headers=adm)).json()["received"] == 100
    await client.put(f"/api/uploads/{up['id']}?offset=100", content=pdf[100:], headers=adm)
    book = await client.post("/api/books/from-upload", json={"upload_id": up["id"], "title": "c", "license": "own"}, headers=adm)
    assert book.status_code == 201
    assert (await client.get(book.json()["file_url"], headers=adm)).content == pdf
