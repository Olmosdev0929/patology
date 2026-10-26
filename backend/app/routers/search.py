"""Global search across the atlas, IGX inventory and (for staff) biopsy cases."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_session
from ..models import Biopsy, Disease, IgxMarker, Role, User
from ..security import current_user
from ..serializers import biopsy_out, disease_out, organ_out

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search")
async def search(q: str = Query(min_length=2, max_length=100), user: User = Depends(current_user),
                 session: AsyncSession = Depends(get_session)):
    like = f"%{q.lower()}%"
    diseases = (await session.execute(
        select(Disease).options(selectinload(Disease.organ)).where(or_(
            func.lower(cast(Disease.name, String)).like(like),
            func.lower(Disease.name_en).like(like),
            func.lower(Disease.icd10).like(like),
            func.lower(cast(Disease.markers, String)).like(like),
        )).limit(8)
    )).scalars()
    out = {"diseases": [{**disease_out(d, full=False), "organ": organ_out(d.organ)} for d in diseases],
           "markers": [], "biopsies": []}
    if user.role != Role.RESIDENT:
        markers = (await session.execute(
            select(IgxMarker).where(or_(func.lower(IgxMarker.name).like(like), func.lower(IgxMarker.clone).like(like))).limit(8)
        )).scalars()
        out["markers"] = [{"id": m.id, "name": m.name, "clone": m.clone, "stock": m.stock} for m in markers]
        cases = (await session.execute(
            select(Biopsy).where(or_(Biopsy.code.ilike(like), Biopsy.patient_name.ilike(like))).limit(8)
        )).scalars()
        out["biopsies"] = [biopsy_out(b, user) for b in cases]
    return out
