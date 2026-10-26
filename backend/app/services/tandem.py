"""Smart Tandem: suggest clinically paired markers, prioritising near-expiry and slow-moving stock.

Only markers with a configured clinical pairing (`tandem_with`) are ever suggested, so the
inventory status changes the *ranking* of indicated tests — it never invents an indication.
The final choice always stays with the pathologist.
"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import IgxMarker
from .inventory import days_to_expiry, status_tags


def _norm(name: str) -> str:
    return name.strip().lower()


async def suggest(session: AsyncSession, selected: list[str], organ: str | None = None, limit: int = 6) -> list[dict]:
    chosen = {_norm(n) for n in selected}
    if not chosen:
        return []
    today = date.today()
    out = []
    for m in (await session.execute(select(IgxMarker))).scalars():
        if _norm(m.name) in chosen or m.stock <= 0:
            continue
        triggers = [t for t in m.tandem_with if _norm(t) in chosen]
        if not triggers:
            continue
        tags = status_tags(m, today)
        score = len(triggers)
        score += 3 if "expiring" in tags else 0
        score += 2 if "slow" in tags else 0
        score += 1 if organ and m.organ == organ else 0
        out.append({
            "name": m.name,
            "clone": m.clone,
            "triggers": triggers,
            "reason": m.reason,
            "tags": tags,
            "stock": m.stock,
            "expiry_date": m.expiry_date.isoformat() if m.expiry_date else None,
            "days_to_expiry": days_to_expiry(m, today),
            "score": score,
        })
    out.sort(key=lambda s: (-s["score"], s["days_to_expiry"] if s["days_to_expiry"] is not None else 10**6, s["name"]))
    return out[:limit]
