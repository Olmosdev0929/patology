"""Idempotent seeding of reference data (atlas, inventory, academy) and optional demo cases."""
import json
import shutil
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import config
from ..models import (
    Biopsy, Book, BookSentence, Disease, IgxLot, IgxMarker, Image, Organ, QuizQuestion, StockMovement,
)
from ..services.inventory import refresh_marker
from . import academy, gallery, inventory

DATA = Path(__file__).parent / "data"


async def seed_atlas(session: AsyncSession) -> None:
    if (await session.execute(select(func.count()).select_from(Organ))).scalar():
        return
    data = json.loads((DATA / "atlas.json").read_text(encoding="utf-8"))
    organs = {}
    for i, o in enumerate(data["organs"]):
        organs[o["slug"]] = Organ(slug=o["slug"], name=o["name"], icon=o["icon"], sort_order=i)
        session.add(organs[o["slug"]])
    await session.flush()
    for d in data["diseases"]:
        session.add(Disease(
            slug=d["slug"], organ_id=organs[d["organ"]].id, name=d["name"], name_en=d["name_en"],
            icd10=d["icd10"], sections=d["sections"], markers=d["markers"], refs=d["refs"],
        ))


async def seed_inventory(session: AsyncSession) -> None:
    existing = set((await session.execute(select(IgxMarker.name))).scalars())
    markers, lots, usage = inventory.build()
    for spec in markers:
        if spec["name"] in existing:
            continue
        marker = IgxMarker(**spec)
        session.add(marker)
        await session.flush()
        used = len(usage.get(marker.name, []))
        for i, (lot_number, expiry, qty) in enumerate(lots.get(marker.name, [])):
            # The historical usage came out of the first (current) lot.
            received = qty + (used if i == 0 else 0)
            session.add(IgxLot(marker_id=marker.id, lot_number=lot_number, expiry_date=expiry,
                               quantity=qty, received_quantity=received))
        # Historical usage so the FEFO tiers (fast / slow movers) are meaningful from day one.
        for ts in usage.get(marker.name, []):
            session.add(StockMovement(marker_id=marker.id, delta=-1, reason="biopsy", created_at=ts))
        await session.flush()
        await refresh_marker(session, marker)


async def seed_academy(session: AsyncSession) -> None:
    for meta, sentences in academy.books():
        if (await session.execute(select(Book.id).where(Book.title == meta["title"]))).scalar():
            continue
        b = Book(**meta)
        b.sentences = [BookSentence(position=i, **s) for i, s in enumerate(sentences)]
        session.add(b)
    if not (await session.execute(select(func.count()).select_from(QuizQuestion))).scalar():
        for q in academy.quiz():
            session.add(QuizQuestion(**q))


async def seed_gallery(session: AsyncSession) -> None:
    """Copy the schematic illustrations into UPLOAD_DIR and register them once."""
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    slugs = dict((await session.execute(select(Disease.slug, Disease.id))).all())
    for spec in gallery.IMAGES:
        filename = f"seed-{spec['file']}"
        target = config.UPLOAD_DIR / filename
        if not target.exists():  # also restores files on a fresh container without a volume
            shutil.copyfile(DATA / "images" / spec["file"], target)
        if (await session.execute(select(Image.id).where(Image.filename == filename))).scalar():
            continue
        session.add(Image(
            filename=filename, content_type="image/svg+xml", kind=spec["kind"], stain=spec["stain"],
            caption={"uz": spec["title"][0], "ru": spec["title"][1]},
            description={"uz": spec["desc"][0], "ru": spec["desc"][1]},
            credit=gallery.CREDIT, disease_id=slugs.get(spec["disease"]),
            pins=[{"x": x, "y": y, "label": {"uz": uz, "ru": ru}} for x, y, uz, ru in spec["pins"]],
        ))


DEMO_CASES = [
    dict(patient_name="Demo Bemor A", patient_age=54, patient_sex="F", organ="breast",
         clinical_suspicion="Chap ko'krak bezida 2 sm tugun, BI-RADS 5", initial_tests=["H&E"],
         selected_markers=[{"name": n, "source": "routine"} for n in ("ER", "PR", "HER2", "Ki-67")]),
    dict(patient_name="Demo Bemor B", patient_age=67, patient_sex="M", organ="lung",
         clinical_suspicion="O'ng o'pka periferik o'smasi, chekuvchi", initial_tests=["H&E"],
         selected_markers=[{"name": n, "source": "routine"} for n in ("TTF-1", "CK5/6")]),
    dict(patient_name="Demo Bemor C", patient_age=61, patient_sex="F", organ="colon",
         clinical_suspicion="Sigmasimon ichak o'smasi", initial_tests=["H&E"],
         selected_markers=[{"name": n, "source": "routine"} for n in ("CK20", "CDX2")]),
]


async def seed_demo(session: AsyncSession) -> None:
    if (await session.execute(select(func.count()).select_from(Biopsy))).scalar():
        return
    from ..services.biopsy import next_code

    for case in DEMO_CASES:
        session.add(Biopsy(code=await next_code(session), **case))
        await session.flush()


async def run(session: AsyncSession, demo: bool = False) -> None:
    await seed_atlas(session)
    await seed_inventory(session)
    await seed_academy(session)
    await session.flush()
    await seed_gallery(session)
    if demo:
        await seed_demo(session)
    await session.commit()
