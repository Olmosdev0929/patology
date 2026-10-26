"""IGX inventory: FEFO lots, status tiers and race-safe stock deduction."""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .. import config
from ..models import Biopsy, IgxLot, IgxMarker, StockMovement, User


class InsufficientStock(Exception):
    def __init__(self, names: list[str]):
        super().__init__(", ".join(names))
        self.names = names


def status_tags(marker: IgxMarker, today: date | None = None) -> list[str]:
    """Inventory tiers shown as badges: expiring / slow / fast (+ stock warnings)."""
    today = today or date.today()
    tags = []
    if marker.stock <= 0:
        tags.append("out_of_stock")
    elif marker.stock <= config.LOW_STOCK_TESTS:
        tags.append("low_stock")
    if marker.expiry_date and marker.stock > 0:
        if (marker.expiry_date - today).days < config.EXPIRY_WARNING_DAYS:
            tags.append("expiring")
    if marker.stock > 0 and marker.used_30d <= config.SLOW_MOVER_MAX_30D:
        tags.append("slow")
    elif marker.used_30d >= config.FAST_MOVER_MIN_30D:
        tags.append("fast")
    return tags


def days_to_expiry(marker: IgxMarker, today: date | None = None) -> int | None:
    if not marker.expiry_date:
        return None
    return (marker.expiry_date - (today or date.today())).days


async def refresh_marker(session: AsyncSession, marker: IgxMarker, today: date | None = None) -> None:
    """Recompute cached stock, earliest usable expiry and 30-day usage from lots and movements."""
    today = today or date.today()
    usable = (IgxLot.marker_id == marker.id) & (IgxLot.quantity > 0) & (IgxLot.expiry_date >= today)
    stock, expiry = (await session.execute(
        select(func.coalesce(func.sum(IgxLot.quantity), 0), func.min(IgxLot.expiry_date)).where(usable)
    )).one()
    since = datetime.now(timezone.utc) - timedelta(days=30)
    used = (await session.execute(
        select(func.coalesce(func.sum(-StockMovement.delta), 0)).where(
            StockMovement.marker_id == marker.id,
            StockMovement.reason == "biopsy",
            StockMovement.created_at >= since,
        )
    )).scalar()
    marker.stock, marker.expiry_date, marker.used_30d = int(stock), expiry, int(used)


async def usage_stats(session: AsyncSession, days: int = 30) -> dict:
    """Consumption overview for the "Sarf statistikasi" tab."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (await session.execute(
        select(StockMovement.created_at, IgxMarker.name)
        .join(IgxMarker, IgxMarker.id == StockMovement.marker_id)
        .where(StockMovement.reason == "biopsy", StockMovement.created_at >= since)
    )).all()
    today = date.today()
    daily = {(today - timedelta(days=i)).isoformat(): 0 for i in range(days - 1, -1, -1)}
    per_marker: dict[str, int] = {}
    for ts, name in rows:
        key = (ts.date() if isinstance(ts, datetime) else ts).isoformat()
        if key in daily:
            daily[key] += 1
        per_marker[name] = per_marker.get(name, 0) + 1
    markers = (await session.execute(select(IgxMarker))).scalars().all()
    expired_left = (await session.execute(
        select(func.coalesce(func.sum(IgxLot.quantity), 0)).where(IgxLot.quantity > 0, IgxLot.expiry_date < today)
    )).scalar()
    return {
        "days": days,
        "total_tests": len(rows),
        "daily": [{"date": d, "count": c} for d, c in daily.items()],
        "top": sorted(({"name": n, "count": c} for n, c in per_marker.items()), key=lambda x: -x["count"])[:10],
        "idle": sorted(m.name for m in markers if m.stock > 0 and m.used_30d == 0),
        "expired_tests_on_shelf": int(expired_left),
        "coverage": sorted(
            ({"name": m.name, "stock": m.stock, "used_30d": m.used_30d,
              "days_of_supply": round(m.stock / (m.used_30d / 30)) if m.used_30d else None} for m in markers),
            key=lambda x: (x["days_of_supply"] is None, x["days_of_supply"] or 0),
        ),
    }


async def refresh_all(session: AsyncSession) -> None:
    for marker in (await session.execute(select(IgxMarker))).scalars():
        await refresh_marker(session, marker)


async def receive_lot(
    session: AsyncSession, marker: IgxMarker, lot_number: str, expiry_date: date, quantity: int, user: User | None
) -> IgxLot:
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    lot = IgxLot(marker_id=marker.id, lot_number=lot_number, expiry_date=expiry_date,
                 quantity=quantity, received_quantity=quantity)
    session.add(lot)
    await session.flush()
    session.add(StockMovement(marker_id=marker.id, lot_id=lot.id, delta=quantity, reason="receive",
                              user_id=user.id if user else None))
    await session.flush()
    await refresh_marker(session, marker)
    return lot


async def deduct_for_biopsy(session: AsyncSession, biopsy: Biopsy, user: User) -> list[dict]:
    """Deduct one test per selected marker, earliest-expiring usable lot first (FEFO).

    Rows are locked with SELECT ... FOR UPDATE in a stable order (by name) so concurrent
    approvals cannot oversell a lot or deadlock. Nothing is changed if any marker is short.
    """
    today = date.today()
    names = sorted({m["name"] for m in biopsy.selected_markers})
    markers = (await session.execute(
        select(IgxMarker).where(IgxMarker.name.in_(names)).order_by(IgxMarker.name).with_for_update()
    )).scalars().all()
    by_name = {m.name: m for m in markers}

    picks: list[tuple[IgxMarker, IgxLot]] = []
    short: list[str] = []
    for name in names:
        marker = by_name.get(name)
        lot = None
        if marker:
            lot = (await session.execute(
                select(IgxLot)
                .where(IgxLot.marker_id == marker.id, IgxLot.quantity > 0, IgxLot.expiry_date >= today)
                .order_by(IgxLot.expiry_date, IgxLot.id)
                .limit(1)
                .with_for_update()
            )).scalar()
        if lot is None:
            short.append(name)
        else:
            picks.append((marker, lot))
    if short:
        raise InsufficientStock(short)

    report = []
    for marker, lot in picks:
        # Captured before the deduction: did this case use a marker that needed using?
        tags = status_tags(marker, today)
        # Conditional decrement is atomic on every backend: it can never take a lot below zero,
        # even where FOR UPDATE is unsupported (SQLite). The caller rolls back on failure.
        res = await session.execute(
            update(IgxLot).where(IgxLot.id == lot.id, IgxLot.quantity > 0)
            .values(quantity=IgxLot.quantity - 1).execution_options(synchronize_session=False)
        )
        if res.rowcount != 1:
            raise InsufficientStock([marker.name])
        session.expire(lot, ["quantity"])
        session.add(StockMovement(marker_id=marker.id, lot_id=lot.id, delta=-1, reason="biopsy",
                                  biopsy_id=biopsy.id, user_id=user.id))
        await session.flush()
        await refresh_marker(session, marker, today)
        report.append({"name": marker.name, "lot": lot.lot_number, "stock_left": marker.stock,
                       "rescued": "expiring" in tags or "slow" in tags})
    return report
