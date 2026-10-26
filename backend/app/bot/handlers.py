"""Incoming bot updates: web login links, language, inline panel approval (the button menu lives in menu.py)."""
import html
import secrets
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import BotCommand, CallbackQuery, MenuButtonWebApp, Message, WebAppInfo
from sqlalchemy import select

from .. import config
from ..database import SessionLocal
from ..models import LoginToken, Role, User
from ..routers.auth import upsert_telegram_user
from ..services import biopsy as workflow
from ..services.inventory import InsufficientStock
from . import menu, notify
from .texts import t

router = Router()


def _tg_dict(u) -> dict:
    return {"id": u.id, "first_name": u.first_name, "last_name": u.last_name,
            "username": u.username, "language_code": u.language_code}


@router.message(Command("login"))
async def login(message: Message):
    async with SessionLocal() as session:
        user = await upsert_telegram_user(session, _tg_dict(message.from_user))
        if not config.WEBAPP_URL:
            await session.commit()
            return await message.answer(t(user.language, "login_no_url"))
        token = secrets.token_urlsafe(32)
        session.add(LoginToken(token=token, user_id=user.id,
                               expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)))
        await session.commit()
    await message.answer(t(user.language, "login_link", url=f"{config.WEBAPP_URL}/#/login?token={token}"),
                         disable_web_page_preview=True)


@router.message(Command("til"))
async def toggle_language(message: Message):
    async with SessionLocal() as session:
        user = await upsert_telegram_user(session, _tg_dict(message.from_user))
        user.language = "ru" if user.language == "uz" else "uz"
        await session.commit()
    await message.answer(t(user.language, "lang_set"))


@router.callback_query(F.data.startswith("approve:"))
async def approve(cb: CallbackQuery):
    code = cb.data.split(":", 1)[1]
    async with SessionLocal() as session:
        user = (await session.execute(select(User).where(User.telegram_id == cb.from_user.id))).scalar()
        lang = user.language if user else "uz"
        if not user or not user.is_active or user.role not in (Role.PATHOLOGIST, Role.SUPER_ADMIN):
            return await cb.answer(t(lang, "forbidden"), show_alert=True)
        try:
            _, report = await workflow.approve(session, code, user)
            await session.commit()
        except LookupError:
            return await cb.answer(t(lang, "not_found"), show_alert=True)
        except workflow.WorkflowError as e:
            key = "no_markers" if "No markers" in str(e) else "already"
            await cb.answer()
            return await cb.message.edit_text(t(lang, key, code=code), parse_mode="HTML")
        except InsufficientStock as e:
            await session.rollback()
            await cb.answer()
            await notify.shortage(code, e.names)
            return await cb.message.answer(t(lang, "shortage", code=code, markers=html.escape(", ".join(e.names))),
                                           parse_mode="HTML")
    items = ", ".join(f"{r['name']} ({r['stock_left']})" for r in report)
    await cb.answer("✅")
    await cb.message.edit_text(t(lang, "approved", code=code, by=html.escape(user.name), items=html.escape(items)),
                               parse_mode="HTML", reply_markup=menu.kb(menu.home_row(lang, f"bx:v:{code}")))
    await notify.low_stock_after([r["name"] for r in report])


def create_bot() -> tuple[Bot, Dispatcher]:
    bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    dp.include_router(router)
    dp.include_router(menu.router)  # last: it has the catch-all text handler
    return bot, dp


COMMANDS = {
    "uz": [("start", "Bot haqida va yo'riqnoma"), ("menu", "Asosiy menyu"), ("atlas", "Atlasdan qidirish"),
           ("inventar", "IGX ombor"), ("login", "Brauzer uchun kirish havolasi"), ("til", "Tilni almashtirish"),
           ("cancel", "Amalni bekor qilish")],
    "ru": [("start", "О боте и инструкция"), ("menu", "Главное меню"), ("atlas", "Поиск по атласу"),
           ("inventar", "Склад IGX"), ("login", "Ссылка для входа в браузере"), ("til", "Сменить язык"),
           ("cancel", "Отменить действие")],
}


async def setup_menu(bot: Bot) -> None:
    await bot.set_my_commands([BotCommand(command=c, description=d) for c, d in COMMANDS["uz"]])
    await bot.set_my_commands([BotCommand(command=c, description=d) for c, d in COMMANDS["ru"]], language_code="ru")
    if config.WEBAPP_URL.startswith("https://"):
        await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="PathoUz", web_app=WebAppInfo(url=config.WEBAPP_URL)))
