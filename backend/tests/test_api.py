import asyncio
from datetime import date, timedelta

import pytest
from sqlalchemy import select, text

from app import config
from app.models import AuditLog, IgxLot, IgxMarker, Role, User
from app.services import inventory

from .conftest import init_data

pytestmark = pytest.mark.asyncio

BREAST = {"patient_name": "Ali Valiyev", "patient_age": 50, "patient_sex": "F", "organ": "breast",
          "clinical_suspicion": "BI-RADS 5",
          "selected_markers": [{"name": n} for n in ("ER", "PR", "HER2", "Ki-67")]}


async def marker(db, name) -> IgxMarker:
    async with db.SessionLocal() as s:
        return (await s.execute(select(IgxMarker).where(IgxMarker.name == name))).scalar()


# ---------------------------------------------------------------- auth & RBAC

async def test_telegram_login_creates_resident_and_promotes_admin(client, monkeypatch):
    r = await client.post("/api/auth/telegram", json={"init_data": init_data(555)})
    assert r.status_code == 200 and r.json()["user"]["role"] == "resident"
    monkeypatch.setattr(config, "SUPER_ADMIN_IDS", {555})
    r = await client.post("/api/auth/telegram", json={"init_data": init_data(555)})
    assert r.json()["user"]["role"] == "super_admin"
    bad = await client.post("/api/auth/telegram", json={"init_data": init_data(555, token="wrong")})
    assert bad.status_code == 401
    old = await client.post("/api/auth/telegram", json={"init_data": init_data(555, auth_date=1)})
    assert old.status_code == 401


async def test_dev_login_disabled_by_default(client):
    assert (await client.post("/api/auth/dev-login", json={})).status_code == 404


async def test_rbac(client, make_user):
    _, resident = await make_user(Role.RESIDENT)
    _, tech = await make_user(Role.TECHNICIAN)
    _, path = await make_user(Role.PATHOLOGIST)
    assert (await client.get("/api/biopsies", headers=resident)).status_code == 403
    assert (await client.get("/api/inventory", headers=resident)).status_code == 403
    assert (await client.get("/api/atlas/organs", headers=resident)).status_code == 200
    assert (await client.get("/api/users", headers=path)).status_code == 403
    assert (await client.get("/api/biopsies")).status_code == 401

    r = await client.post("/api/biopsies", json=BREAST, headers=tech)
    assert r.status_code == 201
    code = r.json()["code"]
    # Technicians get the work-list with initials only
    listed = (await client.get("/api/biopsies", headers=tech)).json()[0]
    assert listed["patient_name"] == "A. V."
    full = (await client.get(f"/api/biopsies/{code}", headers=path)).json()
    assert full["patient_name"] == "Ali Valiyev"
    # Only pathologists approve
    assert (await client.post(f"/api/biopsies/{code}/approve", headers=tech)).status_code == 403


async def test_admin_cannot_demote_self(client, make_user):
    admin, h = await make_user(Role.SUPER_ADMIN)
    r = await client.patch(f"/api/users/{admin.id}", json={"role": "resident"}, headers=h)
    assert r.status_code == 409


# ---------------------------------------------------------------- biopsy workflow

async def test_full_biopsy_workflow(client, make_user, seeded):
    doctor, h = await make_user(Role.PATHOLOGIST, "Dr Karimova")
    r = await client.post("/api/biopsies", json=BREAST, headers=h)
    code = r.json()["code"]
    assert code.startswith(f"B-{date.today().year}-")

    tandem = (await client.get(f"/api/biopsies/{code}/tandem", headers=h)).json()
    names = [s["name"] for s in tandem]
    assert "GATA3" in names and "E-cadherin" in names
    assert "SATB2" not in names  # not clinically paired with a breast receptor panel
    assert tandem[0]["tags"]  # highest-ranked suggestion is expiring and/or slow

    # Doctor adds a tandem marker and a brand-new custom one
    r = await client.post(f"/api/biopsies/{code}/markers", json={"name": "GATA3", "source": "tandem"}, headers=h)
    assert r.json()["biopsy"]["selected_markers"][-1] == {"name": "GATA3", "source": "tandem"}
    r = await client.post(f"/api/biopsies/{code}/markers", json={"name": "TRPS1"}, headers=h)
    assert r.json()["marker"]["is_custom"] and r.json()["marker"]["stock"] == 0

    # Custom marker has no stock yet → approval is refused, nothing is deducted
    er_before = (await marker(seeded, "ER")).stock
    r = await client.post(f"/api/biopsies/{code}/approve", headers=h)
    assert r.status_code == 409 and r.json()["detail"]["markers"] == ["TRPS1"]
    assert (await marker(seeded, "ER")).stock == er_before

    # Remove the custom marker and approve
    panel = [m for m in (await client.get(f"/api/biopsies/{code}", headers=h)).json()["selected_markers"] if m["name"] != "TRPS1"]
    await client.patch(f"/api/biopsies/{code}", json={"selected_markers": panel}, headers=h)
    gata_before = await marker(seeded, "GATA3")
    r = await client.post(f"/api/biopsies/{code}/approve", headers=h)
    assert r.status_code == 200, r.text
    deducted = {d["name"]: d for d in r.json()["deducted"]}
    assert set(deducted) == {"ER", "PR", "HER2", "Ki-67", "GATA3"}
    assert deducted["GATA3"]["rescued"] and not deducted["ER"]["rescued"]
    gata_after = await marker(seeded, "GATA3")
    assert gata_after.stock == gata_before.stock - 1 and gata_after.used_30d == gata_before.used_30d + 1
    async with seeded.SessionLocal() as s:
        assert (await s.get(User, doctor.id)).markers_saved == 1

    # Idempotent: second approval is rejected, no double deduction
    assert (await client.post(f"/api/biopsies/{code}/approve", headers=h)).status_code == 409
    assert (await marker(seeded, "ER")).stock == er_before - 1
    # Panel is frozen after approval
    r = await client.post(f"/api/biopsies/{code}/markers", json={"name": "p63"}, headers=h)
    assert r.status_code == 409

    # Scoring
    r = await client.put(f"/api/biopsies/{code}/scoring", headers=h, json={
        "er": {"percent": 90, "intensity": 3}, "pr": {"percent": 40, "intensity": 2},
        "her2": {"score": 2, "ish_amplified": False}, "ki67": 12})
    s = r.json()["scoring_result"]
    assert s["er"]["total"] == 8 and s["her2"]["status"] == "low" and s["subtype"] == "luminal_a"

    # Consilium
    await client.post(f"/api/biopsies/{code}/consilium", json={"open": True}, headers=h)
    c = await client.post(f"/api/biopsies/{code}/comments", json={"text": "Lobulyar komponent yo'q"}, headers=h)
    assert c.status_code == 201
    other, h2 = await make_user(Role.PATHOLOGIST)
    await client.post(f"/api/biopsies/{code}/comments", json={"text": "Qo'shilaman"}, headers=h2)
    assert len((await client.get(f"/api/biopsies/{code}", headers=h)).json()["consilium_comments"]) == 2

    # Sign-out needs a diagnosis
    assert (await client.post(f"/api/biopsies/{code}/report", headers=h)).status_code == 422
    await client.patch(f"/api/biopsies/{code}", json={"diagnosis": "Invaziv karsinoma NST, G2"}, headers=h)
    r = await client.post(f"/api/biopsies/{code}/report", headers=h)
    assert r.json()["status"] == "reported" and not r.json()["consilium_open"]
    async with seeded.SessionLocal() as s:
        assert (await s.get(User, doctor.id)).cases_done == 1

    admin, ha = await make_user(Role.SUPER_ADMIN)
    kpi = (await client.get("/api/kpi", headers=ha)).json()
    me = next(x for x in kpi["staff"] if x["id"] == doctor.id)
    assert (me["cases_done"], me["markers_saved"], me["panels_approved"]) == (1, 1, 1)


async def test_fefo_skips_expired_and_uses_earliest_lot(client, make_user, seeded):
    _, h = await make_user(Role.PATHOLOGIST)
    async with seeded.SessionLocal() as s:
        cd30 = (await s.execute(select(IgxMarker).where(IgxMarker.name == "CD30"))).scalar()
        s.add(IgxLot(marker_id=cd30.id, lot_number="CD30-SOON", expiry_date=date.today() + timedelta(days=5), quantity=2))
        await s.flush()
        await inventory.refresh_marker(s, cd30)
        await s.commit()
    body = {**BREAST, "organ": "lymph", "selected_markers": [{"name": "CD30"}]}
    code = (await client.post("/api/biopsies", json=body, headers=h)).json()["code"]
    r = await client.post(f"/api/biopsies/{code}/approve", headers=h)
    assert r.json()["deducted"][0]["lot"] == "CD30-SOON"  # not the expired lot, not the later one


async def test_concurrent_approvals_never_oversell(client, make_user, seeded):
    """Two cases race for the last test of a marker: exactly one wins."""
    _, h = await make_user(Role.PATHOLOGIST)
    async with seeded.SessionLocal() as s:
        m = IgxMarker(name="LAST-ONE", description={}, reason={}, lab_passport={}, tandem_with=[])
        s.add(m)
        await s.flush()
        s.add(IgxLot(marker_id=m.id, lot_number="L1", expiry_date=date.today() + timedelta(days=100), quantity=1))
        await s.commit()
    body = {**BREAST, "selected_markers": [{"name": "LAST-ONE"}]}
    codes = [(await client.post("/api/biopsies", json=body, headers=h)).json()["code"] for _ in range(2)]
    results = await asyncio.gather(*(client.post(f"/api/biopsies/{c}/approve", headers=h) for c in codes))
    assert sorted(r.status_code for r in results) == [200, 409]
    async with seeded.SessionLocal() as s:
        lot = (await s.execute(select(IgxLot).where(IgxLot.lot_number == "L1"))).scalar()
        assert lot.quantity == 0


async def test_concurrent_double_approve_same_case(client, make_user, seeded):
    _, h = await make_user(Role.PATHOLOGIST)
    code = (await client.post("/api/biopsies", json=BREAST, headers=h)).json()["code"]
    before = (await marker(seeded, "ER")).stock
    results = await asyncio.gather(*(client.post(f"/api/biopsies/{code}/approve", headers=h) for _ in range(3)))
    assert sorted(r.status_code for r in results) == [200, 409, 409]
    assert (await marker(seeded, "ER")).stock == before - 1


# ---------------------------------------------------------------- inventory

async def test_inventory_tiers_and_lots(client, make_user):
    _, tech = await make_user(Role.TECHNICIAN)
    items = (await client.get("/api/inventory?tag=expiring", headers=tech)).json()
    assert items and all(i["days_to_expiry"] < config.EXPIRY_WARNING_DAYS for i in items)
    fast = {i["name"] for i in (await client.get("/api/inventory?tag=fast", headers=tech)).json()}
    assert {"ER", "Ki-67"} <= fast

    m = (await client.get("/api/inventory?q=gata", headers=tech)).json()[0]
    r = await client.post(f"/api/inventory/{m['id']}/lots", headers=tech,
                          json={"lot_number": "NEW", "expiry_date": str(date.today() + timedelta(days=365)), "quantity": 50})
    assert r.json()["stock"] == m["stock"] + 50
    assert r.json()["expiry_date"] == m["expiry_date"]  # FEFO expiry stays the earliest lot
    r = await client.post(f"/api/inventory/{m['id']}/lots", headers=tech,
                          json={"lot_number": "OLD", "expiry_date": str(date.today() - timedelta(days=1)), "quantity": 5})
    assert r.status_code == 422

    r = await client.put(f"/api/inventory/{m['id']}", headers=tech, json={"lab_passport": {"dilution": "1:300"}})
    assert r.json()["lab_passport"]["dilution"] == "1:300" and not r.json()["passport_verified"]
    r = await client.post(f"/api/inventory/{m['id']}/passport/verify", headers=tech)
    assert r.json()["passport_verified"]

    lot = next(l for l in r.json()["lots"] if l["lot_number"] == "NEW")
    r = await client.post(f"/api/inventory/{m['id']}/adjust", headers=tech, json={"lot_id": lot["id"], "delta": -60})
    assert r.status_code == 409


# ---------------------------------------------------------------- academy

async def test_reader_anki_and_quiz(client, make_user):
    _, h = await make_user(Role.RESIDENT)
    book = (await client.get("/api/books", headers=h)).json()[0]
    sent = (await client.get(f"/api/books/{book['id']}?limit=3", headers=h)).json()["sentences"][0]
    assert sent["en"] and sent["uz"] and sent["ru"]

    card = (await client.post("/api/anki", json={"sentence_id": sent["id"], "deck": "Breast"}, headers=h)).json()
    assert card["front_en"] == sent["en"] and card["back_ru"] == sent["ru"]
    due = (await client.get("/api/anki?due=true", headers=h)).json()
    assert [c["id"] for c in due] == [card["id"]]
    r = (await client.post(f"/api/anki/{card['id']}/review", json={"answer": "good"}, headers=h)).json()
    assert r["interval"] == 1 and r["next_review"] == str(date.today() + timedelta(days=1))
    assert (await client.get("/api/anki?due=true", headers=h)).json() == []
    assert (await client.post(f"/api/anki/{card['id']}/review", json={"answer": "meh"}, headers=h)).status_code == 422

    _, other = await make_user(Role.RESIDENT)
    assert (await client.post(f"/api/anki/{card['id']}/review", json={"answer": "good"}, headers=other)).status_code == 404

    quiz = (await client.get("/api/quiz/daily", headers=h)).json()
    q = quiz["questions"][0]
    assert "correct" not in q
    r = (await client.post(f"/api/quiz/{q['id']}/answer", json={"chosen": 0}, headers=h)).json()
    assert "explanation" in r and r["explanation"]["ru"]
    assert (await client.get("/api/quiz/stats", headers=h)).json()["answered"] == 1


async def test_book_import_admin_only(client, make_user):
    _, res = await make_user(Role.RESIDENT)
    _, adm = await make_user(Role.SUPER_ADMIN)
    body = {"title": "Own notes", "license": "CC BY 4.0", "sentences": [{"en": "Hello", "uz": "Salom", "ru": "Привет"}]}
    assert (await client.post("/api/books/import", json=body, headers=res)).status_code == 403
    assert (await client.post("/api/books/import", json=body, headers=adm)).status_code == 201


# ---------------------------------------------------------------- images

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


async def test_image_upload_and_pins(client, make_user):
    _, path = await make_user(Role.PATHOLOGIST)
    _, res = await make_user(Role.RESIDENT)
    code = (await client.post("/api/biopsies", json=BREAST, headers=path)).json()["code"]

    bad = await client.post("/api/upload-image", headers=path, files={"file": ("x.png", b"not an image", "image/png")})
    assert bad.status_code == 415

    r = await client.post("/api/upload-image", headers=path, files={"file": ("x.png", PNG, "image/png")},
                          data={"kind": "micro", "stain": "H&E", "biopsy_code": code, "caption_uz": "Invaziya"})
    assert r.status_code == 201
    img = r.json()
    assert (await client.get(img["url"], headers=path)).content == PNG
    assert (await client.get(img["url"], headers=res)).status_code == 403  # case image, resident

    r = await client.put(f"/api/images/{img['id']}/pins", headers=path,
                         json={"pins": [{"x": 0.3, "y": 0.6, "label": {"uz": "Mitoz", "ru": "Митоз"}}]})
    assert r.json()["pins"][0]["label"]["ru"] == "Митоз"
    assert (await client.put(f"/api/images/{img['id']}/pins", headers=path, json={"pins": [{"x": 2, "y": 0}]})).status_code == 422

    atlas = await client.post("/api/upload-image", headers=path, files={"file": ("a.png", PNG, "image/png")},
                              data={"kind": "macro", "disease_slug": "skin-bcc"})
    assert (await client.get(atlas.json()["url"], headers=res)).status_code == 200
    listed = (await client.get("/api/images?disease=skin-bcc", headers=res)).json()
    assert [i["id"] for i in listed] == [atlas.json()["id"]]


# ---------------------------------------------------------------- audit

async def test_audit_chain(client, make_user, seeded):
    _, h = await make_user(Role.SUPER_ADMIN)
    await client.post("/api/biopsies", json=BREAST, headers=h)
    entries = (await client.get("/api/audit", headers=h)).json()
    assert entries[0]["action"] == "biopsy.create"
    assert (await client.get("/api/audit/verify", headers=h)).json()["ok"]

    if seeded.engine.dialect.name == "postgresql":
        async with seeded.SessionLocal() as s:
            with pytest.raises(Exception, match="append-only"):
                await s.execute(text("UPDATE audit_logs SET action = 'x'"))
                await s.commit()
    else:  # SQLite has no trigger; tampering must still be detected by the hash chain
        async with seeded.SessionLocal() as s:
            row = (await s.execute(select(AuditLog).order_by(AuditLog.id))).scalars().first()
            row.action = "tampered"
            await s.commit()
        assert not (await client.get("/api/audit/verify", headers=h)).json()["ok"]


async def test_login_link(client, seeded):
    import secrets
    from datetime import datetime, timezone

    from app.models import LoginToken

    async with seeded.SessionLocal() as s:
        u = User(telegram_id=777, name="Web", role=Role.PATHOLOGIST)
        s.add(u)
        await s.flush()
        tok = secrets.token_urlsafe(16)
        s.add(LoginToken(token=tok, user_id=u.id, expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)))
        await s.commit()
    r = await client.post("/api/auth/link", json={"token": tok})
    assert r.status_code == 200 and r.json()["user"]["role"] == "pathologist"
    assert (await client.post("/api/auth/link", json={"token": tok})).status_code == 401  # one-time


# ---------------------------------------------------------------- v6 UI endpoints

async def test_atlas_feed_gallery_and_create(client, make_user):
    _, res = await make_user(Role.RESIDENT)
    _, path = await make_user(Role.PATHOLOGIST)
    feed = (await client.get("/api/atlas/diseases", headers=res)).json()
    idc = next(d for d in feed if d["slug"] == "breast-idc")
    assert idc["summary"]["ru"] and len(idc["images"]) == 2
    assert {i["kind"] for i in idc["images"]} == {"macro", "ihc"}
    lung = (await client.get("/api/atlas/diseases?organ=lung", headers=res)).json()
    assert all(d["organ"]["slug"] == "lung" for d in lung)

    gallery = (await client.get("/api/images", headers=res)).json()
    assert len(gallery) >= 8 and all(g["disease"] for g in gallery)
    ihc = (await client.get("/api/images?kind=ihc", headers=res)).json()
    assert ihc and all(g["kind"] == "ihc" for g in ihc)
    f = await client.get(gallery[0]["url"], headers=res)
    assert f.status_code == 200 and f.headers["content-type"].startswith("image/svg+xml")

    body = {"organ": "lung", "name": {"uz": "Karsinoid", "ru": "Карциноид"}, "name_en": "Carcinoid tumour", "icd10": "C7A",
            "sections": {"definition": {"uz": "Neyroendokrin o'sma", "ru": "Нейроэндокринная опухоль"}}}
    assert (await client.post("/api/atlas/diseases", json=body, headers=res)).status_code == 403
    r = await client.post("/api/atlas/diseases", json=body, headers=path)
    assert r.status_code == 201 and r.json()["slug"] == "carcinoid-tumour"
    assert (await client.post("/api/atlas/diseases", json=body, headers=path)).json()["slug"] == "carcinoid-tumour-2"


async def test_global_search_respects_roles(client, make_user):
    _, res = await make_user(Role.RESIDENT)
    _, path = await make_user(Role.PATHOLOGIST)
    await client.post("/api/biopsies", json=BREAST, headers=path)
    r = (await client.get("/api/search?q=gata3", headers=path)).json()
    assert r["markers"][0]["name"] == "GATA3" and r["diseases"]
    assert (await client.get("/api/search?q=C34", headers=res)).json()["diseases"]
    r = (await client.get("/api/search?q=valiyev", headers=res)).json()
    assert r["biopsies"] == [] and r["markers"] == []
    assert (await client.get("/api/search?q=valiyev", headers=path)).json()["biopsies"]


async def test_inventory_stats_and_capacity(client, make_user):
    _, tech = await make_user(Role.TECHNICIAN)
    stats = (await client.get("/api/inventory/stats", headers=tech)).json()
    assert len(stats["daily"]) == 30 and stats["total_tests"] > 0
    assert stats["top"][0]["count"] >= stats["top"][-1]["count"]
    assert stats["expired_tests_on_shelf"] == 5  # the expired CD30 lot
    ki = next(m for m in (await client.get("/api/inventory?q=ki-67", headers=tech)).json())
    assert ki["capacity"] >= ki["stock"] > 0


async def test_media_and_books_metadata(client, make_user):
    _, res = await make_user(Role.RESIDENT)
    _, path = await make_user(Role.PATHOLOGIST)
    books = (await client.get("/api/books", headers=res)).json()
    assert {b["category"] for b in books} >= {"IGX Qo'llanma", "Grossing Protokol"} and all(b["chapters"] for b in books)
    body = {"kind": "video", "title": {"uz": "HER2 skoring", "ru": "Скоринг HER2"}, "url": "https://www.youtube.com/watch?v=abc"}
    assert (await client.post("/api/media", json=body, headers=res)).status_code == 403
    assert (await client.post("/api/media", json={**body, "url": "javascript:alert(1)"}, headers=path)).status_code == 422
    m = (await client.post("/api/media", json=body, headers=path)).json()
    assert [x["id"] for x in (await client.get("/api/media?kind=video", headers=res)).json()] == [m["id"]]
    assert (await client.delete(f"/api/media/{m['id']}", headers=path)).status_code == 204
