from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import audit, config
from ..database import get_session
from ..models import LoginToken, Role, User
from ..security import current_user, issue_token, validate_init_data
from ..serializers import user_out

router = APIRouter(prefix="/api", tags=["auth"])


class TelegramAuthIn(BaseModel):
    init_data: str


class LinkAuthIn(BaseModel):
    token: str


class DevLoginIn(BaseModel):
    telegram_id: int = 1
    name: str = "Dev User"
    role: Role = Role.SUPER_ADMIN


class MeUpdate(BaseModel):
    language: str | None = Field(default=None, pattern="^(uz|ru)$")
    specialty: str | None = Field(default=None, max_length=200)


async def upsert_telegram_user(session: AsyncSession, tg: dict) -> User:
    """Create on first login (as resident) or refresh name; promote configured super admins."""
    tg_id = int(tg["id"])
    name = " ".join(x for x in (tg.get("first_name"), tg.get("last_name")) if x) or str(tg_id)
    user = (await session.execute(select(User).where(User.telegram_id == tg_id))).scalar()
    if user is None:
        user = User(telegram_id=tg_id, name=name, username=tg.get("username"), role=Role.RESIDENT,
                    language="ru" if tg.get("language_code") == "ru" else "uz")
        session.add(user)
        await session.flush()
        await audit.log(session, user, "user.register", {"telegram_id": tg_id})
    else:
        user.name, user.username = name, tg.get("username")
    if tg_id in config.SUPER_ADMIN_IDS and user.role != Role.SUPER_ADMIN:
        user.role = Role.SUPER_ADMIN
    return user


def _session_payload(user: User) -> dict:
    return {"token": issue_token(user), "user": user_out(user)}


@router.post("/auth/telegram")
async def auth_telegram(body: TelegramAuthIn, session: AsyncSession = Depends(get_session)):
    tg = validate_init_data(body.init_data, config.BOT_TOKEN)
    if not tg:
        raise HTTPException(401, "Invalid Telegram signature")
    user = await upsert_telegram_user(session, tg)
    if not user.is_active:
        raise HTTPException(403, "Account disabled")
    await session.commit()
    return _session_payload(user)


@router.post("/auth/link")
async def auth_link(body: LinkAuthIn, session: AsyncSession = Depends(get_session)):
    """Exchange a one-time token from the bot's /login command for a web session."""
    row = await session.get(LoginToken, body.token, with_for_update=True)
    if not row or row.used or row.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(401, "Link expired")
    row.used = True
    user = await session.get(User, row.user_id)
    if not user or not user.is_active:
        raise HTTPException(403, "Account disabled")
    await audit.log(session, user, "user.web_login", None)
    await session.commit()
    return _session_payload(user)


@router.post("/auth/dev-login")
async def dev_login(body: DevLoginIn, session: AsyncSession = Depends(get_session)):
    if not config.DEV_MODE:
        raise HTTPException(404)
    user = await upsert_telegram_user(session, {"id": body.telegram_id, "first_name": body.name})
    user.role = body.role
    await session.commit()
    return _session_payload(user)


@router.get("/me")
async def me(user: User = Depends(current_user)):
    return user_out(user)


@router.patch("/me")
async def update_me(body: MeUpdate, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(user, key, value)
    await session.commit()
    return user_out(user)
