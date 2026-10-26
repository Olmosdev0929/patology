"""In-bot work with inline buttons: the main things the app does, without opening it.

Every screen is a (text, keyboard) pair; callbacks edit the same message in place. Free text
(lot numbers, patient names, searches) is collected with FSM states. Role checks mirror the API.
"""
import html
import re
import secrets
from datetime import date, datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import selectinload

from .. import audit, config, database
from ..models import (
    AnkiCard, Biopsy, BiopsyStatus, Disease, IgxLot, IgxMarker, LoginToken, QuizAttempt, QuizQuestion, Role,
    StockMovement, User,
)
from ..routers.academy import todays_question_ids
from ..routers.auth import upsert_telegram_user
from ..serializers import mask_name
from ..services import biopsy as workflow
from ..services import inventory, report, sm2, tandem
from . import notify
from .texts import t

router = Router()

PAGE = 10
STAFF = {Role.SUPER_ADMIN, Role.PATHOLOGIST, Role.TECHNICIAN}
TECH = {Role.SUPER_ADMIN, Role.TECHNICIAN}
PATH = {Role.SUPER_ADMIN, Role.PATHOLOGIST}

# Same routine panels as the web intake form (frontend/src/components/MarkerPicker.jsx).
ROUTINE = {
    "breast": ["ER", "PR", "HER2", "Ki-67", "CK5/6"], "lung": ["TTF-1", "Napsin A", "p40", "CK7"],
    "colon": ["CK20", "CDX2", "CK7"], "stomach": ["CD117", "Ki-67"], "liver": ["CK7", "CK20"],
    "kidney": ["PAX8", "CK7"], "prostate": ["NKX3.1", "p63"], "thyroid": ["TTF-1", "PAX8"],
    "skin": ["S100", "SOX10", "HMB45"], "lymph": ["CD20", "CD3", "CD30", "Ki-67"], "cervix": ["p40", "Ki-67"],
    "other": ["CK7", "CK20"],
}
LOC = {
    "uz": {"nuclear": "yadro", "cytoplasmic": "sitoplazma", "membranous": "membrana", "Golgi": "Golji"},
    "ru": {"nuclear": "ядро", "cytoplasmic": "цитоплазма", "membranous": "мембрана", "Golgi": "Гольджи"},
}


class LotForm(StatesGroup):
    number = State()
    expiry = State()
    quantity = State()


class WriteOff(StatesGroup):
    quantity = State()


class Intake(StatesGroup):
    name = State()
    age = State()
    sex = State()
    suspicion = State()
    panel = State()


class Search(StatesGroup):
    marker = State()
    atlas = State()


# ---------------------------------------------------------------- helpers

def btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def kb(*rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[b for b in row if b] for row in rows if any(row)])


def home_row(lang: str, back: str | None = None) -> list:
    return [btn(t(lang, "btn_back"), back) if back else None, btn(t(lang, "btn_menu"), "m:home")]


def tg_dict(u) -> dict:
    return {"id": u.id, "first_name": u.first_name, "last_name": u.last_name,
            "username": u.username, "language_code": u.language_code}


async def load_user(tg_user) -> User:
    async with database.SessionLocal() as s:
        user = await upsert_telegram_user(s, tg_dict(tg_user))
        await s.commit()
    return user


async def show(target: Message | CallbackQuery, text: str, markup: InlineKeyboardMarkup | None = None) -> None:
    """Edit the menu message in place for button presses, send a new one for typed input."""
    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=markup, parse_mode="HTML", disable_web_page_preview=True)
        except TelegramBadRequest as e:
            if "not modified" not in str(e):
                await target.message.answer(text, reply_markup=markup, parse_mode="HTML", disable_web_page_preview=True)
        await target.answer()
    else:
        await target.answer(text, reply_markup=markup, parse_mode="HTML", disable_web_page_preview=True)


async def deny(target: Message | CallbackQuery, lang: str) -> None:
    if isinstance(target, CallbackQuery):
        await target.answer(t(lang, "forbidden"), show_alert=True)
    else:
        await target.answer(t(lang, "forbidden"))


def esc(value) -> str:
    return html.escape(str(value)) if value not in (None, "") else "—"


def loc_text(loc: str | None, lang: str) -> str:
    if not loc:
        return "—"
    return " / ".join(LOC[lang].get(p, p) for p in loc.split("/"))


def parse_date(text: str) -> date | None:
    text = text.strip()
    for pattern in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


def parse_int(text: str) -> int | None:
    text = text.strip()
    return int(text) if re.fullmatch(r"\d{1,6}", text) else None


# ---------------------------------------------------------------- start / menu / guide

def menu_screen(user: User) -> tuple[str, InlineKeyboardMarkup]:
    lang, role = user.language, user.role
    rows = []
    if role in STAFF:
        rows.append([btn(t(lang, "btn_biopsies"), "bx:home"), btn(t(lang, "btn_inventory"), "inv:home")])
        rows.append([btn(t(lang, "btn_stats"), "st:home")])
    rows.append([btn(t(lang, "btn_atlas"), "at:ask"), btn(t(lang, "btn_academy"), "ac:home")])
    if role == Role.SUPER_ADMIN:
        rows.append([btn(t(lang, "btn_admin"), "ad:home")])
    rows.append([btn(t(lang, "btn_guide"), "m:guide"), btn(t(lang, "btn_lang"), "m:lang")])
    rows.append([notify.webapp_button(t(lang, "open_app")), btn(t(lang, "btn_login"), "m:login")])
    return t(lang, "menu_title", role=t(lang, "roles")[role]), kb(*rows)


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    user = await load_user(message.from_user)
    lang = user.language
    await message.answer(
        t(lang, "welcome", name=html.escape(user.name), role=t(lang, "roles")[user.role]) + "\n\n"
        + t(lang, "about", role=t(lang, "roles")[user.role]),
        parse_mode="HTML",
    )
    await message.answer(t(lang, "guide"), parse_mode="HTML")
    await show(message, *menu_screen(user))


@router.message(Command("menu", "menyu"))
async def menu_cmd(message: Message, state: FSMContext):
    await state.clear()
    await show(message, *menu_screen(await load_user(message.from_user)))


@router.message(Command("help", "yordam"))
async def help_cmd(message: Message):
    user = await load_user(message.from_user)
    await message.answer(t(user.language, "guide") + "\n\n" + t(user.language, "help"), parse_mode="HTML",
                         reply_markup=kb([btn(t(user.language, "btn_menu"), "m:home")]))


@router.message(Command("cancel", "bekor"))
async def cancel_cmd(message: Message, state: FSMContext):
    await state.clear()
    user = await load_user(message.from_user)
    await message.answer(t(user.language, "cancelled"))
    await show(message, *menu_screen(user))


@router.callback_query(F.data == "m:home")
async def home_cb(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await show(cb, *menu_screen(await load_user(cb.from_user)))


@router.callback_query(F.data == "m:guide")
async def guide_cb(cb: CallbackQuery):
    user = await load_user(cb.from_user)
    await show(cb, t(user.language, "guide"), kb(home_row(user.language)))


@router.callback_query(F.data == "m:lang")
async def lang_cb(cb: CallbackQuery):
    async with database.SessionLocal() as s:
        user = await upsert_telegram_user(s, tg_dict(cb.from_user))
        user.language = "ru" if user.language == "uz" else "uz"
        await s.commit()
    await show(cb, *menu_screen(user))


@router.callback_query(F.data == "m:login")
async def login_cb(cb: CallbackQuery):
    async with database.SessionLocal() as s:
        user = await upsert_telegram_user(s, tg_dict(cb.from_user))
        if not config.WEBAPP_URL:
            await s.commit()
            return await cb.answer(t(user.language, "login_no_url"), show_alert=True)
        token = secrets.token_urlsafe(32)
        s.add(LoginToken(token=token, user_id=user.id, expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)))
        await s.commit()
    await cb.answer()
    await cb.message.answer(t(user.language, "login_link", url=f"{config.WEBAPP_URL}/#/login?token={token}"),
                            disable_web_page_preview=True)


# ---------------------------------------------------------------- inventory

FILTERS = {"all": "btn_inv_all", "expiring": "btn_inv_expiring", "low_stock": "btn_inv_low", "out_of_stock": "btn_inv_out"}


async def inventory_screen(user: User) -> tuple[str, InlineKeyboardMarkup]:
    lang = user.language
    counts = {"total": 0, "tests": 0, "expiring": 0, "low_stock": 0, "out_of_stock": 0}
    async with database.SessionLocal() as s:
        for m in (await s.execute(select(IgxMarker))).scalars():
            counts["total"] += 1
            counts["tests"] += m.stock
            for tag in inventory.status_tags(m):
                if tag in counts:
                    counts[tag] += 1
    return t(lang, "inv_title", **counts), kb(
        [btn(t(lang, "btn_inv_all"), "inv:l:all:0"), btn(t(lang, "btn_inv_find"), "inv:find")],
        [btn(t(lang, "btn_inv_expiring"), "inv:l:expiring:0"), btn(t(lang, "btn_inv_low"), "inv:l:low_stock:0")],
        [btn(t(lang, "btn_inv_out"), "inv:l:out_of_stock:0")],
        [notify.webapp_button(t(lang, "btn_open_app_inv"), "#/inventory")],
        home_row(lang),
    )


def marker_buttons(markers: list[IgxMarker]) -> list[list]:
    rows, row = [], []
    for m in markers:
        icon = "⛔" if m.stock <= 0 else "🔴" if "expiring" in inventory.status_tags(m) else "⚠️" if m.stock <= config.LOW_STOCK_TESTS else "🟢"
        row.append(btn(f"{icon} {m.name} · {m.stock}", f"inv:m:{m.id}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return rows


@router.message(Command("inventar", "inventory"))
async def inventory_cmd(message: Message, state: FSMContext):
    await state.clear()
    user = await load_user(message.from_user)
    if user.role not in STAFF:
        return await deny(message, user.language)
    await show(message, *await inventory_screen(user))


@router.callback_query(F.data == "inv:home")
async def inventory_cb(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await load_user(cb.from_user)
    if user.role not in STAFF:
        return await deny(cb, user.language)
    await show(cb, *await inventory_screen(user))


@router.callback_query(F.data.startswith("inv:l:"))
async def inventory_list(cb: CallbackQuery):
    user = await load_user(cb.from_user)
    if user.role not in STAFF:
        return await deny(cb, user.language)
    lang = user.language
    _, _, tag, page = cb.data.split(":")
    page = int(page)
    async with database.SessionLocal() as s:
        markers = (await s.execute(select(IgxMarker).order_by(IgxMarker.name))).scalars().all()
    if tag != "all":
        markers = [m for m in markers if tag in inventory.status_tags(m)]
        if tag == "expiring":
            markers.sort(key=lambda m: m.expiry_date or date.max)
    chunk = markers[page * PAGE:(page + 1) * PAGE]
    nav = [btn(t(lang, "btn_prev"), f"inv:l:{tag}:{page - 1}") if page else None,
           btn(t(lang, "btn_more"), f"inv:l:{tag}:{page + 1}") if (page + 1) * PAGE < len(markers) else None]
    text = t(lang, "inv_list", title=t(lang, FILTERS[tag]), n=len(markers)) if markers else t(lang, "empty")
    await show(cb, text, kb(*marker_buttons(chunk), nav, home_row(lang, "inv:home")))


@router.callback_query(F.data == "inv:find")
async def inventory_find(cb: CallbackQuery, state: FSMContext):
    user = await load_user(cb.from_user)
    if user.role not in STAFF:
        return await deny(cb, user.language)
    await state.set_state(Search.marker)
    await show(cb, t(user.language, "inv_find_ask"), kb([btn(t(user.language, "btn_cancel"), "inv:home")]))


@router.message(Search.marker, F.text, ~F.text.startswith("/"))
async def inventory_find_text(message: Message, state: FSMContext):
    user = await load_user(message.from_user)
    lang, q = user.language, message.text.strip()
    norm = re.sub(r"[^a-z0-9]", "", q.lower())
    async with database.SessionLocal() as s:
        markers = (await s.execute(select(IgxMarker).order_by(IgxMarker.name))).scalars().all()
    hits = [m for m in markers if norm and norm in re.sub(r"[^a-z0-9]", "", m.name.lower())][:20]
    await state.clear()
    if len(hits) == 1:
        return await show(message, *await marker_screen(user, hits[0].id))
    text = t(lang, "inv_list", title=html.escape(q), n=len(hits)) if hits else t(lang, "inv_found_none", q=html.escape(q))
    await show(message, text, kb(*marker_buttons(hits), [btn(t(lang, "btn_inv_find"), "inv:find")], home_row(lang, "inv:home")))


async def marker_screen(user: User, marker_id: int) -> tuple[str, InlineKeyboardMarkup]:
    lang = user.language
    async with database.SessionLocal() as s:
        m = (await s.execute(select(IgxMarker).where(IgxMarker.id == marker_id).options(selectinload(IgxMarker.lots)))).scalar()
    if not m:
        return t(lang, "not_found"), kb(home_row(lang, "inv:home"))
    today = date.today()
    lots = [lot for lot in m.lots if lot.quantity > 0]
    lot_text = (t(lang, "lots_head") + "".join(
        t(lang, "lot_line", lot=esc(lot.lot_number), expiry=lot.expiry_date.strftime("%d.%m.%Y"), qty=lot.quantity,
          flag=t(lang, "lot_expired") if lot.expiry_date < today else "")
        for lot in lots)) if lots else ""
    desc = (m.description or {}).get(lang) or ""
    text = t(lang, "marker_card", name=esc(m.name), desc=html.escape(desc), stock=m.stock,
             expiry=m.expiry_date.strftime("%d.%m.%Y") if m.expiry_date else "—", used=m.used_30d,
             loc=loc_text(m.localization, lang), lots=lot_text)
    rows = []
    if user.role in TECH:
        rows.append([btn(t(lang, "btn_lot_add"), f"inv:lot:{m.id}"),
                     btn(t(lang, "btn_write_off"), f"inv:wo:{m.id}") if lots else None])
    rows.append([notify.webapp_button(t(lang, "btn_open_app_inv"), "#/inventory")])
    rows.append(home_row(lang, "inv:home"))
    return text[:4000], kb(*rows)


@router.callback_query(F.data.startswith("inv:m:"))
async def marker_cb(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await load_user(cb.from_user)
    if user.role not in STAFF:
        return await deny(cb, user.language)
    await show(cb, *await marker_screen(user, int(cb.data.split(":")[2])))


# --- receive a lot

@router.callback_query(F.data.startswith("inv:lot:"))
async def lot_start(cb: CallbackQuery, state: FSMContext):
    user = await load_user(cb.from_user)
    if user.role not in TECH:
        return await deny(cb, user.language)
    marker_id = int(cb.data.split(":")[2])
    async with database.SessionLocal() as s:
        m = await s.get(IgxMarker, marker_id)
    if not m:
        return await cb.answer(t(user.language, "not_found"), show_alert=True)
    await state.set_state(LotForm.number)
    await state.update_data(marker_id=m.id, marker_name=m.name)
    await show(cb, t(user.language, "lot_ask_number", name=esc(m.name)),
               kb([btn(t(user.language, "btn_cancel"), f"inv:m:{m.id}")]))


@router.message(LotForm.number, F.text, ~F.text.startswith("/"))
async def lot_number(message: Message, state: FSMContext):
    user = await load_user(message.from_user)
    number = message.text.strip()[:80]
    if not number:
        return
    await state.update_data(lot_number=number)
    await state.set_state(LotForm.expiry)
    data = await state.get_data()
    await message.answer(t(user.language, "lot_ask_expiry"),
                         reply_markup=kb([btn(t(user.language, "btn_cancel"), f"inv:m:{data['marker_id']}")]))


@router.message(LotForm.expiry, F.text, ~F.text.startswith("/"))
async def lot_expiry(message: Message, state: FSMContext):
    user = await load_user(message.from_user)
    expiry = parse_date(message.text)
    if not expiry or expiry < date.today():
        return await message.answer(t(user.language, "lot_bad_date"))
    await state.update_data(expiry=expiry.isoformat())
    await state.set_state(LotForm.quantity)
    await message.answer(t(user.language, "lot_ask_qty"))


@router.message(LotForm.quantity, F.text, ~F.text.startswith("/"))
async def lot_quantity(message: Message, state: FSMContext):
    user = await load_user(message.from_user)
    lang = user.language
    qty = parse_int(message.text)
    if not qty or qty > 100000:
        return await message.answer(t(lang, "bad_number"))
    data = await state.get_data()
    await state.clear()
    if user.role not in TECH:
        return await deny(message, lang)
    expiry = date.fromisoformat(data["expiry"])
    async with database.SessionLocal() as s:
        m = (await s.execute(select(IgxMarker).where(IgxMarker.id == data["marker_id"]).with_for_update())).scalar()
        if not m:
            return await message.answer(t(lang, "not_found"))
        await inventory.receive_lot(s, m, data["lot_number"], expiry, qty, user)
        await audit.log(s, user, "stock.receive", {"name": m.name, "lot": data["lot_number"], "quantity": qty, "via": "bot"})
        await s.commit()
        stock = m.stock
    await message.answer(t(lang, "lot_added", name=esc(data["marker_name"]), lot=esc(data["lot_number"]), qty=qty,
                           expiry=expiry.strftime("%d.%m.%Y"), stock=stock), parse_mode="HTML")
    await show(message, *await marker_screen(user, data["marker_id"]))


# --- write off

@router.callback_query(F.data.startswith("inv:wo:"))
async def writeoff_start(cb: CallbackQuery, state: FSMContext):
    user = await load_user(cb.from_user)
    if user.role not in TECH:
        return await deny(cb, user.language)
    lang = user.language
    marker_id = int(cb.data.split(":")[2])
    async with database.SessionLocal() as s:
        m = (await s.execute(select(IgxMarker).where(IgxMarker.id == marker_id).options(selectinload(IgxMarker.lots)))).scalar()
    lots = [lot for lot in (m.lots if m else []) if lot.quantity > 0]
    if not lots:
        return await cb.answer(t(lang, "no_lots"), show_alert=True)
    await state.clear()
    rows = [[btn(f"{lot.lot_number} · {lot.expiry_date:%d.%m.%Y} · {lot.quantity}", f"inv:wl:{lot.id}")] for lot in lots]
    await show(cb, t(lang, "wo_pick_lot", name=esc(m.name)), kb(*rows, home_row(lang, f"inv:m:{m.id}")))


@router.callback_query(F.data.startswith("inv:wl:"))
async def writeoff_lot(cb: CallbackQuery, state: FSMContext):
    user = await load_user(cb.from_user)
    if user.role not in TECH:
        return await deny(cb, user.language)
    lot_id = int(cb.data.split(":")[2])
    async with database.SessionLocal() as s:
        lot = await s.get(IgxLot, lot_id)
        m = await s.get(IgxMarker, lot.marker_id) if lot else None
    if not lot or not m:
        return await cb.answer(t(user.language, "not_found"), show_alert=True)
    await state.set_state(WriteOff.quantity)
    await state.update_data(lot_id=lot.id, marker_id=m.id, marker_name=m.name)
    await show(cb, t(user.language, "wo_ask_qty", name=esc(m.name), lot=esc(lot.lot_number), qty=lot.quantity),
               kb([btn(t(user.language, "btn_cancel"), f"inv:m:{m.id}")]))


@router.message(WriteOff.quantity, F.text, ~F.text.startswith("/"))
async def writeoff_qty(message: Message, state: FSMContext):
    user = await load_user(message.from_user)
    lang = user.language
    n = parse_int(message.text)
    if not n:
        return await message.answer(t(lang, "bad_number"))
    data = await state.get_data()
    if user.role not in TECH:
        await state.clear()
        return await deny(message, lang)
    async with database.SessionLocal() as s:
        m = (await s.execute(select(IgxMarker).where(IgxMarker.id == data["marker_id"]).with_for_update())).scalar()
        lot = (await s.execute(select(IgxLot).where(IgxLot.id == data["lot_id"]).with_for_update())).scalar()
        if not m or not lot:
            await state.clear()
            return await message.answer(t(lang, "not_found"))
        if n > lot.quantity:
            return await message.answer(t(lang, "wo_too_many", qty=lot.quantity))
        lot.quantity -= n
        s.add(StockMovement(marker_id=m.id, lot_id=lot.id, delta=-n, reason="write_off", user_id=user.id))
        await s.flush()
        await inventory.refresh_marker(s, m)
        await audit.log(s, user, "stock.write_off", {"name": m.name, "lot": lot.lot_number, "delta": -n, "via": "bot"})
        await s.commit()
        stock = m.stock
    await state.clear()
    await message.answer(t(lang, "wo_done", name=esc(data["marker_name"]), n=n, stock=stock), parse_mode="HTML")
    await show(message, *await marker_screen(user, data["marker_id"]))


# ---------------------------------------------------------------- usage statistics

@router.callback_query(F.data == "st:home")
async def stats_cb(cb: CallbackQuery):
    user = await load_user(cb.from_user)
    if user.role not in STAFF:
        return await deny(cb, user.language)
    lang = user.language
    async with database.SessionLocal() as s:
        st = await inventory.usage_stats(s)
    top = "\n".join(f"• {esc(x['name'])} — {x['count']}" for x in st["top"]) or "—"
    cover = "\n".join(f"• {esc(x['name'])} — {x['days_of_supply']} ({x['stock']})"
                      for x in st["coverage"] if x["days_of_supply"] is not None)
    await show(cb, t(lang, "stats", total=st["total_tests"], expired=st["expired_tests_on_shelf"], top=top,
                     cover="\n".join(cover.splitlines()[:10]) or "—"),
               kb([notify.webapp_button(t(lang, "btn_open_app_inv"), "#/inventory")], home_row(lang)))


# ---------------------------------------------------------------- biopsies

def patient_label(b: Biopsy, user: User, lang: str) -> str:
    name = mask_name(b.patient_name) if user.role == Role.TECHNICIAN else b.patient_name
    sex = {"uz": {"M": "Erkak", "F": "Ayol"}, "ru": {"M": "Муж.", "F": "Жен."}}[lang].get(b.patient_sex or "", "")
    return ", ".join(x for x in (name, str(b.patient_age) if b.patient_age is not None else "", sex) if x)


def organ_name(slug: str, lang: str) -> str:
    return report.ORGANS.get(lang, report.ORGANS["uz"]).get(slug, slug)


@router.callback_query(F.data == "bx:home")
async def biopsies_cb(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await load_user(cb.from_user)
    if user.role not in STAFF:
        return await deny(cb, user.language)
    lang = user.language
    async with database.SessionLocal() as s:
        counts = dict((await s.execute(select(Biopsy.status, func.count()).group_by(Biopsy.status))).all())
    await show(cb, t(lang, "bx_title", registered=counts.get("registered", 0), approved=counts.get("approved", 0),
                     reported=counts.get("reported", 0)), kb(
        [btn(t(lang, "btn_bx_new"), "bx:new")],
        [btn(t(lang, "btn_bx_registered"), "bx:l:registered:0"), btn(t(lang, "btn_bx_recent"), "bx:l:all:0")],
        [notify.webapp_button(t(lang, "open_case"), "#/cases")],
        home_row(lang),
    ))


@router.callback_query(F.data.startswith("bx:l:"))
async def biopsy_list(cb: CallbackQuery):
    user = await load_user(cb.from_user)
    if user.role not in STAFF:
        return await deny(cb, user.language)
    lang = user.language
    _, _, status, page = cb.data.split(":")
    page = int(page)
    q = select(Biopsy).order_by(Biopsy.created_at.desc()).offset(page * PAGE).limit(PAGE + 1)
    if status != "all":
        q = q.where(Biopsy.status == status)
    async with database.SessionLocal() as s:
        rows = (await s.execute(q)).scalars().all()
    icons = {"registered": "🕓", "approved": "✅", "reported": "📄"}
    buttons = [[btn(f"{icons.get(b.status, '')} {b.code} · {organ_name(b.organ, lang)}", f"bx:v:{b.code}")] for b in rows[:PAGE]]
    nav = [btn(t(lang, "btn_prev"), f"bx:l:{status}:{page - 1}") if page else None,
           btn(t(lang, "btn_more"), f"bx:l:{status}:{page + 1}") if len(rows) > PAGE else None]
    title = t(lang, "btn_bx_registered") if status == "registered" else t(lang, "btn_bx_recent")
    await show(cb, t(lang, "bx_list", title=title) if rows else t(lang, "empty"),
               kb(*buttons, nav, home_row(lang, "bx:home")))


async def biopsy_screen(user: User, code: str) -> tuple[str, InlineKeyboardMarkup]:
    lang = user.language
    async with database.SessionLocal() as s:
        b = (await s.execute(select(Biopsy).where(Biopsy.code == code))).scalar()
    if not b:
        return t(lang, "not_found"), kb(home_row(lang, "bx:home"))
    text = t(lang, "bx_card", code=esc(b.code), status=t(lang, "status").get(b.status, b.status),
             patient=esc(patient_label(b, user, lang)), organ=esc(organ_name(b.organ, lang)),
             suspicion=esc(b.clinical_suspicion), panel=esc(", ".join(m["name"] for m in b.selected_markers)),
             date=b.created_at.strftime("%d.%m.%Y %H:%M"))
    rows = []
    if b.status == BiopsyStatus.REGISTERED and user.role in PATH:
        rows.append([btn(t(lang, "approve_btn"), f"approve:{b.code}")])
    rows.append([btn(t(lang, "btn_report"), f"bx:p:report:{b.code}"), btn(t(lang, "btn_labels"), f"bx:p:labels:{b.code}")])
    rows.append([notify.webapp_button(t(lang, "open_case"), f"#/cases/{b.code}")])
    rows.append(home_row(lang, "bx:l:all:0"))
    return text, kb(*rows)


@router.callback_query(F.data.startswith("bx:v:"))
async def biopsy_view(cb: CallbackQuery):
    user = await load_user(cb.from_user)
    if user.role not in STAFF:
        return await deny(cb, user.language)
    await show(cb, *await biopsy_screen(user, cb.data.split(":", 2)[2]))


@router.callback_query(F.data.startswith("bx:p:"))
async def biopsy_print(cb: CallbackQuery):
    user = await load_user(cb.from_user)
    if user.role not in STAFF:
        return await deny(cb, user.language)
    _, _, kind, code = cb.data.split(":", 3)
    if not config.WEBAPP_URL:
        return await cb.answer(t(user.language, "login_no_url"), show_alert=True)
    token = report.issue_link_token(code, kind, user.language)
    await cb.answer()
    await cb.message.answer(t(user.language, "print_link", url=f"{config.WEBAPP_URL}/api/print/{kind}/{code}?token={token}"),
                            disable_web_page_preview=True)


# --- intake

@router.callback_query(F.data == "bx:new")
async def intake_start(cb: CallbackQuery, state: FSMContext):
    user = await load_user(cb.from_user)
    if user.role not in STAFF:
        return await deny(cb, user.language)
    lang = user.language
    await state.clear()
    organs = list(ROUTINE)
    rows = [[btn(organ_name(o, lang), f"bx:o:{o}") for o in organs[i:i + 2]] for i in range(0, len(organs), 2)]
    await show(cb, t(lang, "bx_ask_organ"), kb(*rows, [btn(t(lang, "btn_cancel"), "bx:home")]))


@router.callback_query(F.data.startswith("bx:o:"))
async def intake_organ(cb: CallbackQuery, state: FSMContext):
    user = await load_user(cb.from_user)
    if user.role not in STAFF:
        return await deny(cb, user.language)
    organ = cb.data.split(":", 2)[2]
    if organ not in ROUTINE:
        return await cb.answer()
    await state.set_state(Intake.name)
    await state.update_data(organ=organ)
    await show(cb, t(user.language, "bx_ask_name"), kb([btn(t(user.language, "btn_cancel"), "bx:home")]))


@router.message(Intake.name, F.text, ~F.text.startswith("/"))
async def intake_name(message: Message, state: FSMContext):
    user = await load_user(message.from_user)
    name = " ".join(message.text.split())[:200]
    if len(name) < 2:
        return await message.answer(t(user.language, "bx_bad_name"))
    await state.update_data(patient_name=name)
    await state.set_state(Intake.age)
    await message.answer(t(user.language, "bx_ask_age"), reply_markup=kb([btn(t(user.language, "btn_skip"), "bx:age:-")]))


async def ask_sex(target, lang: str, state: FSMContext) -> None:
    await state.set_state(Intake.sex)
    await show(target, t(lang, "bx_ask_sex"), kb([btn(t(lang, "btn_male"), "bx:sex:M"), btn(t(lang, "btn_female"), "bx:sex:F")],
                                                 [btn(t(lang, "btn_skip"), "bx:sex:-")]))


@router.message(Intake.age, F.text, ~F.text.startswith("/"))
async def intake_age(message: Message, state: FSMContext):
    user = await load_user(message.from_user)
    age = parse_int(message.text)
    if age is None or age > 130:
        return await message.answer(t(user.language, "bx_bad_age"))
    await state.update_data(patient_age=age)
    await ask_sex(message, user.language, state)


@router.callback_query(Intake.age, F.data == "bx:age:-")
async def intake_age_skip(cb: CallbackQuery, state: FSMContext):
    user = await load_user(cb.from_user)
    await state.update_data(patient_age=None)
    await ask_sex(cb, user.language, state)


@router.callback_query(Intake.sex, F.data.startswith("bx:sex:"))
async def intake_sex(cb: CallbackQuery, state: FSMContext):
    user = await load_user(cb.from_user)
    sex = cb.data.split(":")[2]
    await state.update_data(patient_sex=sex if sex in ("M", "F") else None)
    await state.set_state(Intake.suspicion)
    await show(cb, t(user.language, "bx_ask_susp"), kb([btn(t(user.language, "btn_skip"), "bx:susp:-")]))


async def panel_screen(lang: str, data: dict) -> tuple[str, InlineKeyboardMarkup, list[str]]:
    selected = data["selected"]
    async with database.SessionLocal() as s:
        suggestions = [x["name"] for x in await tandem.suggest(s, selected, data["organ"])]
    options = list(dict.fromkeys(ROUTINE[data["organ"]] + data.get("extra", []) + selected + suggestions))
    rows, row = [], []
    for i, name in enumerate(options):
        mark = "✅" if name in selected else "✨" if name in suggestions else "▫️"
        row.append(btn(f"{mark} {name}", f"bx:t:{i}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    text = t(lang, "bx_panel", organ=esc(organ_name(data["organ"], lang)), selected=esc(", ".join(selected)))
    return text, kb(*rows, [btn(t(lang, "btn_create"), "bx:ok")], [btn(t(lang, "btn_cancel"), "bx:home")]), options


async def show_panel(target, lang: str, state: FSMContext) -> None:
    data = await state.get_data()
    text, markup, options = await panel_screen(lang, data)
    await state.update_data(options=options)
    await show(target, text, markup)


async def to_panel(target, lang: str, state: FSMContext, suspicion: str | None) -> None:
    data = await state.get_data()
    await state.update_data(clinical_suspicion=suspicion, selected=list(ROUTINE[data["organ"]]), extra=[])
    await state.set_state(Intake.panel)
    await show_panel(target, lang, state)


@router.message(Intake.suspicion, F.text, ~F.text.startswith("/"))
async def intake_suspicion(message: Message, state: FSMContext):
    user = await load_user(message.from_user)
    await to_panel(message, user.language, state, message.text.strip()[:2000] or None)


@router.callback_query(Intake.suspicion, F.data == "bx:susp:-")
async def intake_suspicion_skip(cb: CallbackQuery, state: FSMContext):
    user = await load_user(cb.from_user)
    await to_panel(cb, user.language, state, None)


@router.callback_query(Intake.panel, F.data.startswith("bx:t:"))
async def intake_toggle(cb: CallbackQuery, state: FSMContext):
    user = await load_user(cb.from_user)
    data = await state.get_data()
    i = int(cb.data.split(":")[2])
    options = data.get("options", [])
    if i >= len(options):
        return await cb.answer()
    name, selected = options[i], list(data["selected"])
    selected.remove(name) if name in selected else selected.append(name)
    await state.update_data(selected=selected)
    await show_panel(cb, user.language, state)


@router.message(Intake.panel, F.text, ~F.text.startswith("/"))
async def intake_add_marker(message: Message, state: FSMContext):
    """Typing a name adds any marker (unknown names become custom markers, as in the app)."""
    user = await load_user(message.from_user)
    name = message.text.strip()[:80]
    if not name or name.startswith("/"):
        return
    async with database.SessionLocal() as s:
        known = (await s.execute(select(IgxMarker.name).where(func.lower(IgxMarker.name) == name.lower()))).scalar()
    name = known or name
    data = await state.get_data()
    selected = list(data["selected"]) + ([name] if name not in data["selected"] else [])
    await state.update_data(selected=selected, extra=list(dict.fromkeys(data.get("extra", []) + [name])))
    await show_panel(message, user.language, state)


@router.callback_query(Intake.panel, F.data == "bx:ok")
async def intake_create(cb: CallbackQuery, state: FSMContext):
    user = await load_user(cb.from_user)
    lang = user.language
    if user.role not in STAFF:
        await state.clear()
        return await deny(cb, lang)
    data = await state.get_data()
    if not data["selected"]:
        return await cb.answer(t(lang, "bx_need_marker"), show_alert=True)
    routine = set(ROUTINE[data["organ"]])
    async with database.SessionLocal() as s:
        panel = []
        for name in data["selected"]:
            marker = await workflow.ensure_marker(s, name, user)
            if any(p["name"] == marker.name for p in panel):
                continue
            source = "custom" if marker.is_custom else "routine" if marker.name in routine else "tandem"
            panel.append({"name": marker.name, "source": source})
        b = await workflow.create(s, user, {
            "patient_name": data["patient_name"], "patient_age": data.get("patient_age"),
            "patient_sex": data.get("patient_sex"), "organ": data["organ"],
            "clinical_suspicion": data.get("clinical_suspicion"), "initial_tests": ["H&E"], "selected_markers": panel,
        })
        await s.commit()
        code = b.code
    await state.clear()
    await show(cb, t(lang, "bx_created", code=esc(code), panel=esc(", ".join(p["name"] for p in panel))),
               kb([btn(t(lang, "open_case"), f"bx:v:{code}")], home_row(lang, "bx:home")))
    await notify.new_biopsy(code)


# ---------------------------------------------------------------- atlas

@router.callback_query(F.data == "at:ask")
async def atlas_ask(cb: CallbackQuery, state: FSMContext):
    user = await load_user(cb.from_user)
    await state.set_state(Search.atlas)
    await show(cb, t(user.language, "atlas_ask"), kb(home_row(user.language)))


@router.message(Command("atlas"))
async def atlas_cmd(message: Message, state: FSMContext):
    user = await load_user(message.from_user)
    await state.set_state(Search.atlas)
    await show(message, t(user.language, "atlas_ask"), kb(home_row(user.language)))


@router.message(Search.atlas, F.text, ~F.text.startswith("/"))
async def atlas_search(message: Message, state: FSMContext):
    user = await load_user(message.from_user)
    lang, q = user.language, message.text.strip()[:100]
    if len(q) < 2:
        return await message.answer(t(lang, "atlas_ask"), parse_mode="HTML")
    like = f"%{q.lower()}%"
    async with database.SessionLocal() as s:
        rows = (await s.execute(select(Disease).where(or_(
            func.lower(cast(Disease.name, String)).like(like), func.lower(Disease.name_en).like(like),
            func.lower(Disease.icd10).like(like), func.lower(cast(Disease.markers, String)).like(like),
            func.lower(cast(Disease.sections, String)).like(like),
        )).limit(15))).scalars().all()
    if not rows:
        return await message.answer(t(lang, "atlas_none", q=html.escape(q)), reply_markup=kb(home_row(lang)))
    await state.clear()
    buttons = [[btn((d.name.get(lang) or d.name_en or d.slug)[:60], f"at:d:{d.id}")] for d in rows]
    await show(message, t(lang, "atlas_found", q=html.escape(q), n=len(rows)),
               kb(*buttons, [btn(t(lang, "btn_atlas_again"), "at:ask")], home_row(lang)))


@router.callback_query(F.data.startswith("at:d:"))
async def atlas_disease(cb: CallbackQuery):
    user = await load_user(cb.from_user)
    lang = user.language
    async with database.SessionLocal() as s:
        d = (await s.execute(select(Disease).where(Disease.id == int(cb.data.split(":")[2]))
                             .options(selectinload(Disease.organ)))).scalar()
    if not d:
        return await cb.answer(t(lang, "not_found"), show_alert=True)

    def pick(v):
        return (v.get(lang) or v.get("uz") or "") if isinstance(v, dict) else str(v or "")

    markers = ", ".join(f"{m['name']} {pick(m.get('result'))}".strip() for m in d.markers) or "—"
    definition = pick((d.sections or {}).get("definition", {}))
    text = t(lang, "atlas_card", name=esc(pick(d.name)), name_en=esc(d.name_en), icd=esc(d.icd10),
             organ=esc(pick(d.organ.name)), definition=html.escape(definition[:1500]), markers=html.escape(markers[:1200]))
    await show(cb, text[:4000], kb([notify.webapp_button(t(lang, "btn_open_disease"), f"#/atlas/disease/{d.slug}")],
                                   [btn(t(lang, "btn_atlas_again"), "at:ask")], home_row(lang)))


# ---------------------------------------------------------------- academy

@router.callback_query(F.data == "ac:home")
async def academy_cb(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await load_user(cb.from_user)
    lang = user.language
    async with database.SessionLocal() as s:
        todays = await todays_question_ids(s)
        done = (await s.execute(select(func.count(func.distinct(QuizAttempt.question_id))).where(
            QuizAttempt.user_id == user.id, QuizAttempt.question_id.in_(todays) if todays else False,
            func.date(QuizAttempt.created_at) == date.today()))).scalar() if todays else 0
        answered = (await s.execute(select(func.count()).where(QuizAttempt.user_id == user.id))).scalar()
        correct = (await s.execute(select(func.count()).where(QuizAttempt.user_id == user.id, QuizAttempt.is_correct))).scalar()
        cards = (await s.execute(select(func.count()).where(AnkiCard.user_id == user.id))).scalar()
        due = (await s.execute(select(func.count()).where(AnkiCard.user_id == user.id, AnkiCard.next_review <= date.today()))).scalar()
    await show(cb, t(lang, "academy", done=done, total=len(todays), due=due, cards=cards, correct=correct, answered=answered), kb(
        [btn(t(lang, "btn_quiz"), "ac:q:0"), btn(t(lang, "btn_anki"), "ac:a")],
        [notify.webapp_button(t(lang, "btn_open_academy"), "#/academy")],
        home_row(lang),
    ))


LETTERS = "ABCDEF"


@router.callback_query(F.data.startswith("ac:q:"))
async def quiz_question(cb: CallbackQuery):
    user = await load_user(cb.from_user)
    lang = user.language
    i = int(cb.data.split(":")[2])
    async with database.SessionLocal() as s:
        todays = await todays_question_ids(s)
        if i >= len(todays):
            correct = (await s.execute(select(func.count(func.distinct(QuizAttempt.question_id))).where(
                QuizAttempt.user_id == user.id, QuizAttempt.question_id.in_(todays or [0]), QuizAttempt.is_correct,
                func.date(QuizAttempt.created_at) == date.today()))).scalar()
            return await show(cb, t(lang, "quiz_done", correct=correct, n=len(todays)), kb([btn(t(lang, "btn_academy"), "ac:home")], home_row(lang)))
        q = await s.get(QuizQuestion, todays[i])
    options = "\n".join(f"<b>{LETTERS[j]})</b> {html.escape(o.get(lang) or o.get('uz', ''))}" for j, o in enumerate(q.options))
    text = t(lang, "quiz_q", i=i + 1, n=len(todays), text=html.escape(q.case_text.get(lang) or q.case_text.get("uz", "")), options=options)
    await show(cb, text[:4000], kb([btn(LETTERS[j], f"ac:x:{i}:{j}") for j in range(len(q.options))], home_row(lang, "ac:home")))


@router.callback_query(F.data.startswith("ac:x:"))
async def quiz_answer(cb: CallbackQuery):
    user = await load_user(cb.from_user)
    lang = user.language
    _, _, i, j = cb.data.split(":")
    i, j = int(i), int(j)
    async with database.SessionLocal() as s:
        todays = await todays_question_ids(s)
        if i >= len(todays):
            return await cb.answer()
        q = await s.get(QuizQuestion, todays[i])
        if j >= len(q.options):
            return await cb.answer()
        ok = j == q.correct
        s.add(QuizAttempt(user_id=user.id, question_id=q.id, chosen=j, is_correct=ok))
        await s.commit()
    verdict = t(lang, "quiz_right") if ok else t(lang, "quiz_wrong", letter=LETTERS[q.correct])
    explanation = html.escape((q.explanation or {}).get(lang) or (q.explanation or {}).get("uz", ""))
    case = html.escape(q.case_text.get(lang) or q.case_text.get("uz", ""))
    await show(cb, f"🎯 {case}\n\n{verdict}\n\n{explanation}"[:4000],
               kb([btn(t(lang, "btn_next"), f"ac:q:{i + 1}")], home_row(lang, "ac:home")))


async def anki_next(cb: CallbackQuery, user: User) -> None:
    lang = user.language
    async with database.SessionLocal() as s:
        due = (await s.execute(select(AnkiCard).where(AnkiCard.user_id == user.id, AnkiCard.next_review <= date.today())
                               .order_by(AnkiCard.next_review, AnkiCard.id).limit(51))).scalars().all()
    if not due:
        return await show(cb, t(lang, "anki_none"), kb([notify.webapp_button(t(lang, "btn_open_academy"), "#/academy")], home_row(lang, "ac:home")))
    c = due[0]
    front = c.front_uz if lang == "uz" else c.front_ru
    await show(cb, t(lang, "anki_front", left=len(due) if len(due) <= 50 else "50+", front=html.escape(front or c.front_en or "")),
               kb([btn(t(lang, "btn_show"), f"ac:s:{c.id}")], home_row(lang, "ac:home")))


@router.callback_query(F.data == "ac:a")
async def anki_cb(cb: CallbackQuery):
    await anki_next(cb, await load_user(cb.from_user))


@router.callback_query(F.data.startswith("ac:s:"))
async def anki_show(cb: CallbackQuery):
    user = await load_user(cb.from_user)
    lang = user.language
    async with database.SessionLocal() as s:
        c = await s.get(AnkiCard, int(cb.data.split(":")[2]))
    if not c or c.user_id != user.id:
        return await cb.answer(t(lang, "not_found"), show_alert=True)
    front = (c.front_uz if lang == "uz" else c.front_ru) or c.front_en or ""
    back = (c.back_uz if lang == "uz" else c.back_ru) or ""
    await show(cb, t(lang, "anki_back", front=html.escape(front), back=html.escape(back))[:4000], kb(
        [btn(t(lang, "btn_again"), f"ac:r:{c.id}:again"), btn(t(lang, "btn_hard"), f"ac:r:{c.id}:hard")],
        [btn(t(lang, "btn_good"), f"ac:r:{c.id}:good"), btn(t(lang, "btn_easy"), f"ac:r:{c.id}:easy")],
        home_row(lang, "ac:home"),
    ))


@router.callback_query(F.data.startswith("ac:r:"))
async def anki_review(cb: CallbackQuery):
    user = await load_user(cb.from_user)
    _, _, card_id, answer = cb.data.split(":")
    if answer not in ("again", "hard", "good", "easy"):
        return await cb.answer()
    async with database.SessionLocal() as s:
        c = await s.get(AnkiCard, int(card_id), with_for_update=True)
        if not c or c.user_id != user.id:
            return await cb.answer(t(user.language, "not_found"), show_alert=True)
        state, next_day = sm2.review(sm2.CardState(c.interval, c.reps, c.easiness, c.lapses), answer)
        c.interval, c.reps, c.easiness, c.lapses = state.interval, state.reps, state.easiness, state.lapses
        c.next_review = next_day
        await s.commit()
    await anki_next(cb, user)


# ---------------------------------------------------------------- admin

ROLE_ORDER = [Role.SUPER_ADMIN, Role.PATHOLOGIST, Role.TECHNICIAN, Role.RESIDENT]


@router.callback_query(F.data == "ad:home")
async def admin_cb(cb: CallbackQuery):
    user = await load_user(cb.from_user)
    if user.role != Role.SUPER_ADMIN:
        return await deny(cb, user.language)
    lang = user.language
    async with database.SessionLocal() as s:
        users = (await s.execute(select(func.count()).select_from(User))).scalar()
        active = (await s.execute(select(func.count()).select_from(User).where(User.is_active))).scalar()
        biopsies = (await s.execute(select(func.count()).select_from(Biopsy))).scalar()
    await show(cb, t(lang, "admin", users=users, active=active, biopsies=biopsies), kb(
        [btn(t(lang, "btn_users"), "ad:l:0")],
        [notify.webapp_button(t(lang, "btn_admin"), "#/admin")],
        home_row(lang),
    ))


@router.callback_query(F.data.startswith("ad:l:"))
async def admin_users(cb: CallbackQuery):
    user = await load_user(cb.from_user)
    if user.role != Role.SUPER_ADMIN:
        return await deny(cb, user.language)
    lang = user.language
    page = int(cb.data.split(":")[2])
    async with database.SessionLocal() as s:
        rows = (await s.execute(select(User).order_by(User.role, User.name).offset(page * PAGE).limit(PAGE + 1))).scalars().all()
    icon = {r: t(lang, "roles")[r].split()[0] for r in ROLE_ORDER}
    buttons = [[btn(f"{icon.get(u.role, '')} {u.name[:40]}{'' if u.is_active else ' ⛔'}", f"ad:u:{u.id}")] for u in rows[:PAGE]]
    nav = [btn(t(lang, "btn_prev"), f"ad:l:{page - 1}") if page else None,
           btn(t(lang, "btn_more"), f"ad:l:{page + 1}") if len(rows) > PAGE else None]
    await show(cb, t(lang, "users_list"), kb(*buttons, nav, home_row(lang, "ad:home")))


async def user_screen(admin: User, user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    lang = admin.language
    async with database.SessionLocal() as s:
        u = await s.get(User, user_id)
    if not u:
        return t(lang, "not_found"), kb(home_row(lang, "ad:l:0"))
    text = t(lang, "user_card", name=esc(u.name), username=f" (@{html.escape(u.username)})" if u.username else "",
             role=t(lang, "roles")[u.role], state=t(lang, "state_active" if u.is_active else "state_blocked"), cases=u.cases_done)
    roles = [btn(("• " if u.role == r else "") + t(lang, "roles")[r], f"ad:r:{u.id}:{r.value}") for r in ROLE_ORDER]
    return text, kb(roles[:2], roles[2:],
                    [btn(t(lang, "btn_block" if u.is_active else "btn_unblock"), f"ad:b:{u.id}")],
                    home_row(lang, "ad:l:0"))


@router.callback_query(F.data.startswith("ad:u:"))
async def admin_user(cb: CallbackQuery):
    user = await load_user(cb.from_user)
    if user.role != Role.SUPER_ADMIN:
        return await deny(cb, user.language)
    await show(cb, *await user_screen(user, int(cb.data.split(":")[2])))


@router.callback_query(F.data.startswith("ad:r:") | F.data.startswith("ad:b:"))
async def admin_update(cb: CallbackQuery):
    admin = await load_user(cb.from_user)
    lang = admin.language
    if admin.role != Role.SUPER_ADMIN:
        return await deny(cb, lang)
    parts = cb.data.split(":")
    target_id = int(parts[2])
    async with database.SessionLocal() as s:
        target = await s.get(User, target_id, with_for_update=True)
        if not target:
            return await cb.answer(t(lang, "not_found"), show_alert=True)
        if parts[1] == "r":
            try:
                change = {"role": Role(parts[3])}
            except ValueError:
                return await cb.answer()
        else:
            change = {"is_active": not target.is_active}
        if target.id == admin.id and (change.get("role", Role.SUPER_ADMIN) != Role.SUPER_ADMIN or change.get("is_active") is False):
            return await cb.answer(t(lang, "self_change"), show_alert=True)
        for key, value in change.items():
            setattr(target, key, value)
        await audit.log(s, admin, "user.update", {"user": target.name, **{k: str(v) for k, v in change.items()}, "via": "bot"})
        await s.commit()
    await cb.answer(t(lang, "user_updated"))
    await show(cb, *await user_screen(admin, target_id))


# ---------------------------------------------------------------- fallback

@router.message(StateFilter(None), F.text & ~F.text.startswith("/"))
async def fallback(message: Message):
    user = await load_user(message.from_user)
    await show(message, *menu_screen(user))
