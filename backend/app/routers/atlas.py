"""Disease & macro/micro atlas (read for everyone signed in, edit for pathologists/admins)."""
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import audit
from ..database import get_session
from ..models import Disease, Image, Organ, User
from ..security import PathologistOnly, current_user
from ..seed.templates import TEMPLATES
from ..serializers import disease_out, image_out, organ_out

router = APIRouter(prefix="/api/atlas", tags=["atlas"])


class DiseaseUpdate(BaseModel):
    name: dict[str, str] | None = None
    name_en: str | None = None
    icd10: str | None = None
    sections: dict[str, dict[str, str]] | None = None
    markers: list[dict[str, str]] | None = None
    refs: str | None = None


class DiseaseIn(BaseModel):
    organ: str
    name: dict[str, str]
    name_en: str | None = None
    icd10: str | None = None
    slug: str | None = None
    sections: dict[str, dict[str, str]] = {}
    markers: list[dict] = []
    refs: str | None = None


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:70] or "disease"


async def _previews(session: AsyncSession, disease_ids: list[int], per: int = 2) -> dict[int, list]:
    if not disease_ids:
        return {}
    rows = (await session.execute(
        select(Image).where(Image.disease_id.in_(disease_ids)).order_by(Image.id)
    )).scalars()
    out: dict[int, list] = {}
    for img in rows:
        lst = out.setdefault(img.disease_id, [])
        if len(lst) < per:
            lst.append(image_out(img))
    return out


def _card(d: Disease, previews: dict) -> dict:
    return {**disease_out(d, full=False), "organ": organ_out(d.organ),
            "summary": (d.sections or {}).get("definition", {}), "images": previews.get(d.id, [])}


@router.get("/diseases")
async def list_diseases(organ: str | None = None, _: User = Depends(current_user),
                        session: AsyncSession = Depends(get_session)):
    """Disease cards for the atlas feed: summary + first two images."""
    q = select(Disease).join(Organ).options(selectinload(Disease.organ)).order_by(Organ.sort_order, Disease.id)
    if organ:
        q = q.where(Organ.slug == organ)
    diseases = (await session.execute(q)).scalars().all()
    previews = await _previews(session, [d.id for d in diseases])
    return [_card(d, previews) for d in diseases]


@router.post("/diseases", status_code=201)
async def create_disease(body: DiseaseIn, user: User = Depends(PathologistOnly),
                         session: AsyncSession = Depends(get_session)):
    organ = (await session.execute(select(Organ).where(Organ.slug == body.organ))).scalar()
    if not organ:
        raise HTTPException(404, "Organ not found")
    if not (body.name.get("uz") or body.name.get("ru")):
        raise HTTPException(422, "Name is required")
    base = body.slug or _slugify(body.name_en or body.name.get("uz") or body.name.get("ru"))
    slug, n = base, 1
    while (await session.execute(select(Disease.id).where(Disease.slug == slug))).scalar():
        n += 1
        slug = f"{base}-{n}"
    d = Disease(slug=slug, organ_id=organ.id, name=body.name, name_en=body.name_en, icd10=body.icd10,
                sections=body.sections, markers=body.markers, refs=body.refs)
    session.add(d)
    await session.flush()
    await audit.log(session, user, "atlas.create", {"slug": slug})
    await session.commit()
    d = (await session.execute(select(Disease).where(Disease.id == d.id).options(selectinload(Disease.organ)))).scalar()
    return disease_out(d)


@router.get("/organs")
async def organs(_: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(
        select(Organ, func.count(Disease.id)).outerjoin(Disease).group_by(Organ.id).order_by(Organ.sort_order)
    )).all()
    return [organ_out(o, n) for o, n in rows]


@router.get("/organs/{slug}")
async def organ(slug: str, _: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    o = (await session.execute(
        select(Organ).where(Organ.slug == slug).options(selectinload(Organ.diseases))
    )).scalar()
    if not o:
        raise HTTPException(404, "Organ not found")
    return {**organ_out(o), "diseases": [disease_out(d, full=False) for d in o.diseases]}


@router.get("/diseases/{slug}")
async def disease(slug: str, _: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    d = (await session.execute(
        select(Disease).where(Disease.slug == slug).options(selectinload(Disease.organ))
    )).scalar()
    if not d:
        raise HTTPException(404, "Disease not found")
    return disease_out(d)


@router.put("/diseases/{slug}")
async def update_disease(slug: str, body: DiseaseUpdate, user: User = Depends(PathologistOnly),
                         session: AsyncSession = Depends(get_session)):
    d = (await session.execute(
        select(Disease).where(Disease.slug == slug).options(selectinload(Disease.organ))
    )).scalar()
    if not d:
        raise HTTPException(404, "Disease not found")
    changes = body.model_dump(exclude_none=True)
    for key, value in changes.items():
        setattr(d, key, value)
    await audit.log(session, user, "atlas.update", {"slug": slug, "fields": sorted(changes)})
    await session.commit()
    await session.refresh(d, ["updated_at"])
    return disease_out(d)


@router.get("/search")
async def search(q: str = Query(min_length=2, max_length=100), _: User = Depends(current_user),
                 session: AsyncSession = Depends(get_session)):
    like = f"%{q.lower()}%"
    rows = (await session.execute(
        select(Disease).options(selectinload(Disease.organ)).where(or_(
            func.lower(cast(Disease.name, String)).like(like),
            func.lower(Disease.name_en).like(like),
            func.lower(Disease.icd10).like(like),
            func.lower(cast(Disease.sections, String)).like(like),
            func.lower(cast(Disease.markers, String)).like(like),
        )).limit(30)
    )).scalars()
    return [{**disease_out(d, full=False), "organ": organ_out(d.organ)} for d in rows]


@router.get("/templates")
async def templates(_: User = Depends(current_user)):
    """Localized macro/micro description templates for report writing."""
    return TEMPLATES
