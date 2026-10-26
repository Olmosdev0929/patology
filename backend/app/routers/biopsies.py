"""Biopsy intake, marker panels, approval (stock deduction), scoring, sign-out and consilium."""
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import audit
from ..bot import notify
from ..database import get_session
from ..models import Biopsy, BiopsyStatus, Image, Role, User
from ..security import PathologistOnly, StaffOnly
from ..serializers import biopsy_out, marker_out
from ..services import biopsy as workflow
from ..services import report, scoring, tandem
from ..services.inventory import InsufficientStock

router = APIRouter(prefix="/api/biopsies", tags=["biopsies"])

MarkerSource = Literal["routine", "tandem", "custom"]


class PanelMarker(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    source: MarkerSource = "routine"


class BiopsyIn(BaseModel):
    patient_name: str = Field(min_length=2, max_length=200)
    patient_age: int | None = Field(default=None, ge=0, le=130)
    patient_sex: Literal["M", "F"] | None = None
    organ: str = Field(min_length=1, max_length=50)
    clinical_suspicion: str | None = Field(default=None, max_length=2000)
    initial_tests: list[str] = []
    selected_markers: list[PanelMarker] = []


class BiopsyUpdate(BaseModel):
    clinical_suspicion: str | None = None
    selected_markers: list[PanelMarker] | None = None
    macro_text: str | None = None
    micro_text: str | None = None
    diagnosis: str | None = None


class AddMarkerIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    source: MarkerSource = "custom"


class AllredIn(BaseModel):
    percent: float = Field(ge=0, le=100)
    intensity: int = Field(ge=0, le=3)


class Her2In(BaseModel):
    score: int | None = Field(default=None, ge=0, le=3)
    pattern: str | None = None
    ish_amplified: bool | None = None


class ScoringIn(BaseModel):
    er: AllredIn | None = None
    pr: AllredIn | None = None
    her2: Her2In | None = None
    ki67: float | None = Field(default=None, ge=0, le=100)
    ki67_cutoff: float = Field(default=20.0, gt=0, lt=100)


class CommentIn(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    image_ids: list[int] = []


class ConsiliumToggle(BaseModel):
    open: bool


async def _get(session: AsyncSession, code: str, lock: bool = False) -> Biopsy:
    q = select(Biopsy).where(Biopsy.code == code)
    if lock:
        q = q.with_for_update()
    biopsy = (await session.execute(q)).scalar()
    if not biopsy:
        raise HTTPException(404, "Case not found")
    return biopsy


def _dedupe(markers: list[PanelMarker]) -> list[dict]:
    seen, out = set(), []
    for m in markers:
        key = m.name.strip().lower()
        if key not in seen:
            seen.add(key)
            out.append({"name": m.name.strip(), "source": m.source})
    return out


async def _canonical_panel(session: AsyncSession, markers: list[PanelMarker], user: User) -> list[dict]:
    """Resolve names against the inventory (registering unknown ones as custom markers)."""
    panel = []
    for item in _dedupe(markers):
        marker = await workflow.ensure_marker(session, item["name"], user)
        panel.append({"name": marker.name, "source": "custom" if marker.is_custom else item["source"]})
    return panel


@router.get("")
async def list_biopsies(
    status: BiopsyStatus | None = None, q: str | None = None, consilium: bool | None = None,
    limit: int = Query(100, le=500),
    user: User = Depends(StaffOnly), session: AsyncSession = Depends(get_session),
):
    query = select(Biopsy).order_by(Biopsy.created_at.desc()).limit(limit)
    if status:
        query = query.where(Biopsy.status == status)
    if consilium is not None:
        query = query.where(Biopsy.consilium_open == consilium)
    if q:
        like = f"%{q}%"
        query = query.where(or_(Biopsy.code.ilike(like), Biopsy.patient_name.ilike(like)))
    return [biopsy_out(b, user) for b in (await session.execute(query)).scalars()]


@router.post("", status_code=201)
async def create_biopsy(body: BiopsyIn, background: BackgroundTasks,
                        user: User = Depends(StaffOnly), session: AsyncSession = Depends(get_session)):
    data = body.model_dump(exclude={"selected_markers"})
    data["selected_markers"] = await _canonical_panel(session, body.selected_markers, user)
    biopsy = await workflow.create(session, user, data)
    await session.commit()
    background.add_task(notify.new_biopsy, biopsy.code)
    return biopsy_out(biopsy, user)


@router.get("/{code}")
async def get_biopsy(code: str, user: User = Depends(StaffOnly), session: AsyncSession = Depends(get_session)):
    biopsy = await _get(session, code)
    images = (await session.execute(select(Image.id).where(Image.biopsy_id == biopsy.id))).scalars().all()
    return {**biopsy_out(biopsy, user), "image_ids": images}


@router.patch("/{code}")
async def update_biopsy(code: str, body: BiopsyUpdate, user: User = Depends(PathologistOnly),
                        session: AsyncSession = Depends(get_session)):
    biopsy = await _get(session, code, lock=True)
    if biopsy.status == BiopsyStatus.REPORTED:
        raise HTTPException(409, "Case is signed out")
    changes = body.model_dump(exclude_none=True, exclude={"selected_markers"})
    if body.selected_markers is not None:
        if biopsy.status != BiopsyStatus.REGISTERED:
            raise HTTPException(409, "Panel is already approved")
        biopsy.selected_markers = await _canonical_panel(session, body.selected_markers, user)
        changes["selected_markers"] = [m["name"] for m in biopsy.selected_markers]
    for key in ("clinical_suspicion", "macro_text", "micro_text", "diagnosis"):
        if key in changes:
            setattr(biopsy, key, changes[key])
    await audit.log(session, user, "biopsy.update", {"code": code, "fields": sorted(changes)})
    await session.commit()
    return biopsy_out(biopsy, user)


@router.post("/{code}/markers")
async def add_marker(code: str, body: AddMarkerIn, user: User = Depends(PathologistOnly),
                     session: AsyncSession = Depends(get_session)):
    """Doctor's custom choice: add any inventory marker or a brand-new name to the panel."""
    biopsy = await _get(session, code, lock=True)
    if biopsy.status != BiopsyStatus.REGISTERED:
        raise HTTPException(409, "Panel is already approved")
    marker = await workflow.ensure_marker(session, body.name, user)
    if all(m["name"].lower() != marker.name.lower() for m in biopsy.selected_markers):
        source = "custom" if marker.is_custom else body.source
        biopsy.selected_markers = [*biopsy.selected_markers, {"name": marker.name, "source": source}]
    await session.commit()
    return {"biopsy": biopsy_out(biopsy, user), "marker": marker_out(marker)}


@router.post("/{code}/approve")
async def approve(code: str, background: BackgroundTasks, user: User = Depends(PathologistOnly),
                  session: AsyncSession = Depends(get_session)):
    try:
        biopsy, report = await workflow.approve(session, code, user)
    except LookupError:
        raise HTTPException(404, "Case not found")
    except workflow.WorkflowError as e:
        raise HTTPException(409, str(e))
    except InsufficientStock as e:
        await session.rollback()
        background.add_task(notify.shortage, code, e.names)
        raise HTTPException(409, {"error": "insufficient_stock", "markers": e.names})
    await session.commit()
    background.add_task(notify.low_stock_after, [r["name"] for r in report])
    return {"biopsy": biopsy_out(biopsy, user), "deducted": report}


@router.put("/{code}/scoring")
async def put_scoring(code: str, body: ScoringIn, user: User = Depends(PathologistOnly),
                      session: AsyncSession = Depends(get_session)):
    biopsy = await _get(session, code, lock=True)
    if biopsy.status == BiopsyStatus.REPORTED:
        raise HTTPException(409, "Case is signed out")
    try:
        result = scoring.compute(body.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(422, str(e))
    result["scored_by"] = user.name
    result["scored_at"] = datetime.now(timezone.utc).isoformat()
    biopsy.scoring_result = result
    await audit.log(session, user, "biopsy.scoring", {"code": code, "subtype": result.get("subtype")})
    await session.commit()
    return biopsy_out(biopsy, user)


@router.post("/{code}/report")
async def sign_out(code: str, user: User = Depends(PathologistOnly), session: AsyncSession = Depends(get_session)):
    biopsy = await _get(session, code, lock=True)
    if biopsy.status != BiopsyStatus.APPROVED:
        raise HTTPException(409, "Only approved cases can be signed out")
    if not (biopsy.diagnosis or "").strip():
        raise HTTPException(422, "Diagnosis is required")
    biopsy.status = BiopsyStatus.REPORTED
    biopsy.consilium_open = False
    user.cases_done += 1
    await audit.log(session, user, "biopsy.report", {"code": code})
    await session.commit()
    return biopsy_out(biopsy, user)


@router.post("/{code}/consilium")
async def toggle_consilium(code: str, body: ConsiliumToggle, background: BackgroundTasks,
                           user: User = Depends(PathologistOnly), session: AsyncSession = Depends(get_session)):
    biopsy = await _get(session, code, lock=True)
    biopsy.consilium_open = body.open
    await audit.log(session, user, "consilium.open" if body.open else "consilium.close", {"code": code})
    await session.commit()
    if body.open:
        background.add_task(notify.consilium_opened, code, user.name)
    return biopsy_out(biopsy, user)


@router.post("/{code}/comments", status_code=201)
async def add_comment(code: str, body: CommentIn, user: User = Depends(PathologistOnly),
                      session: AsyncSession = Depends(get_session)):
    # Row lock: concurrent comments must not overwrite each other's JSON append.
    biopsy = await _get(session, code, lock=True)
    if body.image_ids:
        found = set((await session.execute(
            select(Image.id).where(Image.id.in_(body.image_ids), Image.biopsy_id == biopsy.id)
        )).scalars())
        if found != set(body.image_ids):
            raise HTTPException(422, "Images must belong to this case")
    comment = {
        "id": uuid.uuid4().hex[:12], "user_id": user.id, "user_name": user.name, "role": user.role,
        "text": body.text, "image_ids": body.image_ids, "created_at": datetime.now(timezone.utc).isoformat(),
    }
    biopsy.consilium_comments = [*biopsy.consilium_comments, comment]
    await audit.log(session, user, "consilium.comment", {"code": code})
    await session.commit()
    return comment


@router.get("/{code}/tandem")
async def case_tandem(code: str, user: User = Depends(StaffOnly), session: AsyncSession = Depends(get_session)):
    biopsy = await _get(session, code)
    return await tandem.suggest(session, [m["name"] for m in biopsy.selected_markers], biopsy.organ)



class PrintLinkIn(BaseModel):
    kind: Literal["report", "labels"] = "report"
    lang: Literal["uz", "ru"] = "uz"


@router.post("/{code}/print-link")
async def print_link(code: str, body: PrintLinkIn, user: User = Depends(StaffOnly),
                     session: AsyncSession = Depends(get_session)):
    """Short-lived link that opens the printable page in the system browser (Telegram can't print)."""
    await _get(session, code)
    if body.kind == "report" and user.role == Role.TECHNICIAN:
        raise HTTPException(403, "Insufficient role")
    token = report.issue_link_token(code, body.kind, body.lang)
    return {"url": f"/api/print/{body.kind}/{code}?token={token}"}


print_router = APIRouter(prefix="/api/print", tags=["print"])


@print_router.get("/{kind}/{code}", response_class=HTMLResponse)
async def print_page(kind: Literal["report", "labels"], code: str, token: str,
                     session: AsyncSession = Depends(get_session)):
    lang = report.check_link_token(token, code, kind)
    if not lang:
        raise HTTPException(401, "Link expired")
    b = await _get(session, code)
    if kind == "labels":
        return HTMLResponse(report.render_labels(b, lang))
    approver = (await session.get(User, b.approved_by)).name if b.approved_by else None
    return HTMLResponse(report.render_report(b, approver, lang))
