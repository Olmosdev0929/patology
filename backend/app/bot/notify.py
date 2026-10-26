"""Outgoing Telegram notifications. Every function is a no-op when the bot is not running.

Messages carry case codes only — never patient names — because Telegram chats leave the LIS.
"""
import html
import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from sqlalchemy import select

from .. import config
from ..database import SessionLocal
from ..models import Biopsy, IgxMarker, Role, User
from ..services.inventory import status_tags
from .texts import t

log = logging.getLogger(__name__)
bot: Bot | None = None  # set by main.py when the bot starts


def webapp_button(text: str, path: str = "") -> InlineKeyboardButton | None:
    if not config.WEBAPP_URL.startswith("https://"):
        return None
    return InlineKeyboardButton(text=text, web_app=WebAppInfo(url=f"{config.WEBAPP_URL}/{path}"))


def keyboard(*rows) -> InlineKeyboardMarkup | None:
    rows = [[b for b in row if b] for row in rows]
    rows = [r for r in rows if r]
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


async def _recipients(session, roles: set[Role]) -> list[User]:
    return list((await session.execute(
        select(User).where(User.role.in_(roles | {Role.SUPER_ADMIN}), User.is_active, User.telegram_id.is_not(None))
    )).scalars())


async def _send(users: list[User], build) -> None:
    for u in users:
        text, markup = build(u.language)
        try:
            await bot.send_message(u.telegram_id, text, reply_markup=markup, parse_mode="HTML")
        except Exception as e:  # user blocked the bot, etc. — never break the request flow
            log.warning("notify %s failed: %s", u.telegram_id, e)


def approve_keyboard(lang: str, code: str) -> InlineKeyboardMarkup | None:
    return keyboard(
        [InlineKeyboardButton(text=t(lang, "approve_btn"), callback_data=f"approve:{code}")],
        [webapp_button(t(lang, "open_case"), f"#/cases/{code}")],
    )


async def new_biopsy(code: str) -> None:
    if not bot:
        return
    async with SessionLocal() as session:
        b = (await session.execute(select(Biopsy).where(Biopsy.code == code))).scalar()
        if not b:
            return
        markers = ", ".join(m["name"] for m in b.selected_markers) or "—"
        users = await _recipients(session, {Role.PATHOLOGIST})
    await _send(users, lambda lang: (
        t(lang, "new_biopsy", code=code, organ=html.escape(b.organ), markers=html.escape(markers)),
        approve_keyboard(lang, code),
    ))


async def shortage(code: str, names: list[str]) -> None:
    if not bot:
        return
    async with SessionLocal() as session:
        users = await _recipients(session, {Role.TECHNICIAN})
    items = html.escape(", ".join(names))
    await _send(users, lambda lang: (t(lang, "shortage", code=code, markers=items), keyboard([webapp_button(t(lang, "open_case"), "#/inventory")])))


async def low_stock_after(names: list[str]) -> None:
    if not bot or not names:
        return
    async with SessionLocal() as session:
        markers = (await session.execute(select(IgxMarker).where(IgxMarker.name.in_(names)))).scalars().all()
        low = [m for m in markers if {"low_stock", "out_of_stock"} & set(status_tags(m))]
        if not low:
            return
        users = await _recipients(session, {Role.TECHNICIAN})
    items = html.escape(", ".join(f"{m.name} ({m.stock})" for m in low))
    await _send(users, lambda lang: (t(lang, "low_stock", items=items), None))


async def consilium_opened(code: str, by: str) -> None:
    if not bot:
        return
    async with SessionLocal() as session:
        users = await _recipients(session, {Role.PATHOLOGIST})
    await _send(users, lambda lang: (t(lang, "consilium", code=code, by=html.escape(by)),
                                     keyboard([webapp_button(t(lang, "open_case"), f"#/cases/{code}")])))


async def expiry_digest() -> None:
    """Daily FEFO reminder for technicians and admins."""
    if not bot:
        return
    async with SessionLocal() as session:
        markers = (await session.execute(select(IgxMarker).order_by(IgxMarker.expiry_date))).scalars().all()
        expiring = [m for m in markers if "expiring" in status_tags(m)]
        if not expiring:
            return
        users = await _recipients(session, {Role.TECHNICIAN})
    items = "\n".join(f"• {html.escape(m.name)} — {m.expiry_date.isoformat()} ({m.stock})" for m in expiring)
    await _send(users, lambda lang: (t(lang, "expiring", items=items), keyboard([webapp_button(t(lang, "open_app"), "#/inventory")])))
