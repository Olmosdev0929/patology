"""Biopsy workflow shared by the REST API and the Telegram bot."""
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .. import audit
from ..models import Biopsy, BiopsyStatus, IgxMarker, User
from .inventory import deduct_for_biopsy


class WorkflowError(Exception):
    """Raised for invalid state transitions (mapped to HTTP 409)."""


async def next_code(session: AsyncSession, year: int | None = None) -> str:
    year = year or datetime.now(timezone.utc).year
    prefix = f"B-{year}-"
    last = (await session.execute(
        select(func.max(Biopsy.code)).where(Biopsy.code.like(prefix + "%"), func.length(Biopsy.code) == len(prefix) + 3)
    )).scalar()
    seq = int(last.rsplit("-", 1)[1]) + 1 if last else 1
    return f"{prefix}{seq:03d}" if seq < 1000 else f"{prefix}{seq}"


async def create(session: AsyncSession, user: User, data: dict) -> Biopsy:
    """Insert with a fresh case code; retries if two intakes race for the same number."""
    for _ in range(5):
        biopsy = Biopsy(code=await next_code(session), created_by=user.id, **data)
        try:
            async with session.begin_nested():
                session.add(biopsy)
        except IntegrityError:
            continue
        await audit.log(session, user, "biopsy.create", {"code": biopsy.code, "organ": biopsy.organ})
        return biopsy
    raise WorkflowError("Could not allocate case code")


async def get_locked(session: AsyncSession, code: str) -> Biopsy | None:
    return (await session.execute(select(Biopsy).where(Biopsy.code == code).with_for_update())).scalar()


async def ensure_marker(session: AsyncSession, name: str, user: User) -> IgxMarker:
    """Find a marker by name (case-insensitive) or register a custom one with zero stock."""
    name = name.strip()
    marker = (await session.execute(select(IgxMarker).where(func.lower(IgxMarker.name) == name.lower()))).scalar()
    if marker:
        return marker
    marker = IgxMarker(name=name, is_custom=True, description={}, reason={}, lab_passport={}, tandem_with=[])
    session.add(marker)
    await session.flush()
    await audit.log(session, user, "marker.custom_create", {"name": name})
    return marker


async def approve(session: AsyncSession, code: str, user: User) -> tuple[Biopsy, list[dict]]:
    """Approve the IHC panel: claim the case, deduct stock (FEFO), credit KPI, audit. Caller commits.

    The status change is a conditional UPDATE issued first, so concurrent approvals of the same
    case serialize on it and only one can win; any later failure is rolled back by the caller.
    """
    biopsy = (await session.execute(select(Biopsy).where(Biopsy.code == code))).scalar()
    if biopsy is None:
        raise LookupError(code)
    if not biopsy.selected_markers:
        raise WorkflowError("No markers selected")
    claimed = await session.execute(
        update(Biopsy)
        .where(Biopsy.id == biopsy.id, Biopsy.status == BiopsyStatus.REGISTERED)
        .values(status=BiopsyStatus.APPROVED, approved_by=user.id, approved_at=datetime.now(timezone.utc))
        .execution_options(synchronize_session=False)
    )
    if claimed.rowcount != 1:
        raise WorkflowError("Panel already approved")
    await session.refresh(biopsy)

    report = await deduct_for_biopsy(session, biopsy, user)  # may raise InsufficientStock
    rescued = sum(1 for r in report if r["rescued"])
    user.markers_saved += rescued
    await audit.log(session, user, "biopsy.approve",
                    {"code": code, "tests": len(report), "markers": [r["name"] for r in report], "rescued": rescued})
    return biopsy, report
