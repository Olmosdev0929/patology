"""IGX inventory: list with FEFO tiers, marker cards with lab passports, lot receiving."""
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import audit
from ..database import get_session
from ..models import IgxLot, IgxMarker, StockMovement, User
from ..security import StaffOnly, TechnicianOnly
from ..serializers import marker_out
from ..services import inventory, tandem

router = APIRouter(prefix="/api", tags=["inventory"])


class Localized(BaseModel):
    uz: str = ""
    ru: str = ""


class LabPassport(BaseModel):
    retrieval_buffer: str | None = None      # e.g. "EDTA pH 9.0"
    retrieval_time_min: int | None = None
    dilution: str | None = None              # e.g. "1:100" or "RTU"
    incubation_min: int | None = None
    control_tissue: str | None = None
    notes: str | None = None


class MarkerIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    clone: str | None = None
    vendor: str | None = None
    organ: str | None = None
    localization: str | None = None
    description: Localized = Localized()
    tandem_with: list[str] = []
    reason: Localized = Localized()
    lab_passport: LabPassport = LabPassport()


class MarkerUpdate(BaseModel):
    clone: str | None = None
    vendor: str | None = None
    organ: str | None = None
    localization: str | None = None
    description: Localized | None = None
    tandem_with: list[str] | None = None
    reason: Localized | None = None
    lab_passport: LabPassport | None = None


class LotIn(BaseModel):
    lot_number: str = Field(min_length=1, max_length=80)
    expiry_date: date
    quantity: int = Field(gt=0, le=100000)


class AdjustIn(BaseModel):
    lot_id: int
    delta: int = Field(ne=0)
    reason: str = Field(default="adjust", pattern="^(adjust|write_off)$")


class TandemIn(BaseModel):
    markers: list[str]
    organ: str | None = None


async def _load(session: AsyncSession, marker_id: int, lock: bool = False) -> IgxMarker:
    q = select(IgxMarker).where(IgxMarker.id == marker_id).options(selectinload(IgxMarker.lots))
    if lock:
        q = q.with_for_update()
    marker = (await session.execute(q)).scalar()
    if not marker:
        raise HTTPException(404, "Marker not found")
    return marker


@router.get("/inventory")
async def list_inventory(
    tag: str | None = Query(None, pattern="^(expiring|slow|fast|low_stock|out_of_stock)$"),
    q: str | None = None,
    _: User = Depends(StaffOnly), session: AsyncSession = Depends(get_session),
):
    query = select(IgxMarker).order_by(IgxMarker.name)
    if q:
        query = query.where(func.lower(IgxMarker.name).contains(q.lower()))
    capacity = dict((await session.execute(
        select(IgxLot.marker_id, func.sum(IgxLot.received_quantity))
        .where(IgxLot.quantity > 0, IgxLot.expiry_date >= date.today()).group_by(IgxLot.marker_id)
    )).all())
    items = [{**marker_out(m), "capacity": int(capacity.get(m.id) or 0)} for m in (await session.execute(query)).scalars()]
    if tag:
        items = [m for m in items if tag in m["tags"]]
    return items


@router.get("/inventory/summary")
async def inventory_summary(_: User = Depends(StaffOnly), session: AsyncSession = Depends(get_session)):
    counts = {"total": 0, "expiring": 0, "slow": 0, "fast": 0, "low_stock": 0, "out_of_stock": 0}
    for m in (await session.execute(select(IgxMarker))).scalars():
        counts["total"] += 1
        for t in inventory.status_tags(m):
            counts[t] += 1
    return counts


@router.get("/inventory/stats")
async def inventory_stats(_: User = Depends(StaffOnly), session: AsyncSession = Depends(get_session)):
    return await inventory.usage_stats(session)


@router.get("/inventory/{marker_id}")
async def get_marker(marker_id: int, _: User = Depends(StaffOnly), session: AsyncSession = Depends(get_session)):
    return marker_out(await _load(session, marker_id), with_lots=True)


@router.post("/inventory", status_code=201)
async def create_marker(body: MarkerIn, user: User = Depends(TechnicianOnly), session: AsyncSession = Depends(get_session)):
    data = body.model_dump()
    marker = IgxMarker(**data)
    session.add(marker)
    try:
        await session.flush()
    except IntegrityError:
        raise HTTPException(409, "Marker already exists")
    await audit.log(session, user, "marker.create", {"name": marker.name})
    await session.commit()
    return marker_out(await _load(session, marker.id), with_lots=True)


@router.put("/inventory/{marker_id}")
async def update_marker(marker_id: int, body: MarkerUpdate, user: User = Depends(TechnicianOnly),
                        session: AsyncSession = Depends(get_session)):
    marker = await _load(session, marker_id, lock=True)
    changes = body.model_dump(exclude_none=True)
    for key, value in changes.items():
        setattr(marker, key, value)
    if "lab_passport" in changes:
        # Any protocol change needs a fresh technical verification.
        marker.passport_verified_at = None
        marker.passport_verified_by = None
    await audit.log(session, user, "marker.update", {"name": marker.name, "fields": sorted(changes)})
    await session.commit()
    return marker_out(await _load(session, marker_id), with_lots=True)


@router.post("/inventory/{marker_id}/passport/verify")
async def verify_passport(marker_id: int, user: User = Depends(TechnicianOnly), session: AsyncSession = Depends(get_session)):
    marker = await _load(session, marker_id, lock=True)
    marker.passport_verified_at = datetime.now(timezone.utc)
    marker.passport_verified_by = user.id
    await audit.log(session, user, "marker.passport_verify", {"name": marker.name})
    await session.commit()
    return marker_out(marker, with_lots=True)


@router.post("/inventory/{marker_id}/lots", status_code=201)
async def receive_lot(marker_id: int, body: LotIn, user: User = Depends(TechnicianOnly),
                      session: AsyncSession = Depends(get_session)):
    marker = await _load(session, marker_id, lock=True)
    if body.expiry_date < date.today():
        raise HTTPException(422, "Lot is already expired")
    await inventory.receive_lot(session, marker, body.lot_number, body.expiry_date, body.quantity, user)
    await audit.log(session, user, "stock.receive",
                    {"name": marker.name, "lot": body.lot_number, "quantity": body.quantity})
    await session.commit()
    session.expire(marker)
    return marker_out(await _load(session, marker_id), with_lots=True)


@router.post("/inventory/{marker_id}/adjust")
async def adjust_stock(marker_id: int, body: AdjustIn, user: User = Depends(TechnicianOnly),
                       session: AsyncSession = Depends(get_session)):
    marker = await _load(session, marker_id, lock=True)
    lot = (await session.execute(
        select(IgxLot).where(IgxLot.id == body.lot_id, IgxLot.marker_id == marker.id).with_for_update()
    )).scalar()
    if not lot:
        raise HTTPException(404, "Lot not found")
    if lot.quantity + body.delta < 0:
        raise HTTPException(409, "Stock cannot go below zero")
    lot.quantity += body.delta
    session.add(StockMovement(marker_id=marker.id, lot_id=lot.id, delta=body.delta, reason=body.reason, user_id=user.id))
    await session.flush()
    await inventory.refresh_marker(session, marker)
    await audit.log(session, user, f"stock.{body.reason}", {"name": marker.name, "lot": lot.lot_number, "delta": body.delta})
    await session.commit()
    session.expire(marker)
    return marker_out(await _load(session, marker_id), with_lots=True)


@router.post("/tandem/suggest")
async def tandem_suggest(body: TandemIn, _: User = Depends(StaffOnly), session: AsyncSession = Depends(get_session)):
    return await tandem.suggest(session, body.markers, body.organ)
