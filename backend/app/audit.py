"""Hash-chained audit ledger."""
import hashlib
import json

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AuditLog, User, utcnow

GENESIS = "0" * 64


def _digest(prev_hash: str, created_at: str, user_name: str, action: str, details) -> str:
    body = json.dumps([prev_hash, created_at, user_name, action, details], ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(body.encode()).hexdigest()


async def log(session: AsyncSession, user: User | None, action: str, details: dict | None = None) -> None:
    """Append an entry in the caller's transaction (committed together with the change it describes)."""
    if session.bind.dialect.name == "postgresql":
        # Serialize writers so the hash chain never forks.
        await session.execute(text("SELECT pg_advisory_xact_lock(4242)"))
    prev = (await session.execute(select(AuditLog.hash).order_by(AuditLog.id.desc()).limit(1))).scalar()
    created = utcnow()
    name = user.name if user else "system"
    entry = AuditLog(
        created_at=created, user_id=user.id if user else None, user_name=name,
        action=action, details=details, prev_hash=prev or GENESIS,
        hash=_digest(prev or GENESIS, created.isoformat(), name, action, details),
    )
    session.add(entry)
    await session.flush()


async def verify_chain(session: AsyncSession) -> dict:
    """Recompute every hash; returns the first broken entry id if tampering is detected."""
    prev = GENESIS
    count = 0
    for row in (await session.execute(select(AuditLog).order_by(AuditLog.id))).scalars():
        created = row.created_at.isoformat() if row.created_at.tzinfo else row.created_at.replace(tzinfo=utcnow().tzinfo).isoformat()
        if row.prev_hash != prev or row.hash != _digest(prev, created, row.user_name, row.action, row.details):
            return {"ok": False, "broken_at": row.id, "checked": count}
        prev = row.hash
        count += 1
    return {"ok": True, "checked": count}
