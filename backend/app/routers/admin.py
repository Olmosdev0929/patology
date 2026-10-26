"""Super admin: staff management, KPI, audit ledger."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import audit, config
from ..database import get_session
from ..models import AuditLog, Biopsy, BiopsyStatus, Book, Role, User
from ..security import AdminOnly
from ..serializers import user_out
from ..services import books

router = APIRouter(prefix="/api", tags=["admin"])


class UserUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None
    specialty: str | None = None


@router.get("/users")
async def list_users(_: User = Depends(AdminOnly), session: AsyncSession = Depends(get_session)):
    users = (await session.execute(select(User).order_by(User.role, User.name))).scalars()
    return [user_out(u) for u in users]


@router.patch("/users/{user_id}")
async def update_user(user_id: int, body: UserUpdate, admin: User = Depends(AdminOnly),
                      session: AsyncSession = Depends(get_session)):
    target = await session.get(User, user_id)
    if not target:
        raise HTTPException(404, "User not found")
    changes = body.model_dump(exclude_none=True)
    if target.id == admin.id and (changes.get("role", Role.SUPER_ADMIN) != Role.SUPER_ADMIN or changes.get("is_active") is False):
        raise HTTPException(409, "You cannot demote or disable yourself")
    for key, value in changes.items():
        setattr(target, key, value)
    await audit.log(session, admin, "user.update", {"user": target.name, **{k: str(v) for k, v in changes.items()}})
    await session.commit()
    return user_out(target)


@router.get("/kpi")
async def kpi(_: User = Depends(AdminOnly), session: AsyncSession = Depends(get_session)):
    """Per-physician workload: cases signed out, panels approved, slow/expiring markers put to use."""
    approved = dict((await session.execute(
        select(Biopsy.approved_by, func.count()).where(Biopsy.approved_by.is_not(None)).group_by(Biopsy.approved_by)
    )).all())
    users = (await session.execute(
        select(User).where(User.role.in_([Role.PATHOLOGIST, Role.SUPER_ADMIN])).order_by(User.cases_done.desc())
    )).scalars()
    status_counts = dict((await session.execute(select(Biopsy.status, func.count()).group_by(Biopsy.status))).all())
    return {
        "staff": [{**user_out(u), "panels_approved": approved.get(u.id, 0)} for u in users],
        "cases": {s.value: status_counts.get(s.value, 0) for s in BiopsyStatus},
    }


@router.get("/audit")
async def audit_list(
    limit: int = Query(50, le=200), before_id: int | None = None,
    _: User = Depends(AdminOnly), session: AsyncSession = Depends(get_session),
):
    q = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
    if before_id:
        q = q.where(AuditLog.id < before_id)
    rows = (await session.execute(q)).scalars()
    return [
        {"id": r.id, "created_at": r.created_at.isoformat(), "user_name": r.user_name, "action": r.action,
         "details": r.details, "hash": r.hash[:12]}
        for r in rows
    ]


@router.get("/audit/verify")
async def audit_verify(_: User = Depends(AdminOnly), session: AsyncSession = Depends(get_session)):
    return await audit.verify_chain(session)


@router.get("/storage")
async def storage(_: User = Depends(AdminOnly), session: AsyncSession = Depends(get_session)):
    """Volume usage, so admins see how much room is left for large books."""
    stats = books.storage_stats()
    stats["book_count"] = (await session.execute(
        select(func.count()).select_from(Book).where(Book.file_name.is_not(None))
    )).scalar()
    stats["max_book_mb"] = config.MAX_BOOK_MB
    return stats
