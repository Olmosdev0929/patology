"""The in-bot button menu, driven end to end through aiogram's dispatcher with a recording session."""
from datetime import date, datetime, timezone
from itertools import count

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import AnswerCallbackQuery, EditMessageText, SendMessage
from aiogram.types import CallbackQuery, Chat, Message, Update
from aiogram.types import User as TgUser
from sqlalchemy import select

from app.models import Biopsy, IgxLot, IgxMarker, QuizAttempt, Role, StockMovement, User

from .conftest import BOT_TOKEN

pytestmark = pytest.mark.asyncio
_ids = count(1)


class RecordingSession(BaseSession):
    """Answers every Bot API call locally and keeps what the bot sent."""

    def __init__(self):
        super().__init__()
        self.calls = []

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        if isinstance(method, (SendMessage, EditMessageText)):
            return Message(message_id=next(_ids), date=datetime.now(timezone.utc),
                           chat=Chat(id=method.chat_id or 1, type="private"), text=method.text,
                           reply_markup=method.reply_markup)
        return True

    async def close(self):
        pass

    async def stream_content(self, *args, **kwargs):  # pragma: no cover - not used
        yield b""


class Chat_:
    """One user's conversation with the bot."""

    def __init__(self, dp, bot, session, tg_id):
        self.dp, self.bot, self.session, self.tg_id = dp, bot, session, tg_id
        self.user = TgUser(id=tg_id, is_bot=False, first_name="Test", language_code="uz")
        self.chat = Chat(id=tg_id, type="private")

    def _msg(self, text):
        return Message(message_id=next(_ids), date=datetime.now(timezone.utc), chat=self.chat, from_user=self.user, text=text)

    async def say(self, text):
        self.session.calls.clear()
        await self.dp.feed_update(self.bot, Update(update_id=next(_ids), message=self._msg(text)))
        return self

    async def press(self, data):
        self.session.calls.clear()
        cb = CallbackQuery(id=str(next(_ids)), from_user=self.user, chat_instance="t", data=data, message=self._msg("menu"))
        await self.dp.feed_update(self.bot, Update(update_id=next(_ids), callback_query=cb))
        return self

    @property
    def texts(self):
        return [c.text for c in self.session.calls if isinstance(c, (SendMessage, EditMessageText))]

    @property
    def alerts(self):
        return [c.text for c in self.session.calls if isinstance(c, AnswerCallbackQuery) and c.show_alert]

    def buttons(self):
        out = {}
        for c in self.session.calls:
            if isinstance(c, (SendMessage, EditMessageText)) and c.reply_markup:
                for row in c.reply_markup.inline_keyboard:
                    for b in row:
                        out[b.text] = b.callback_data
        return out


@pytest.fixture
async def bot_chat(seeded):
    from app.bot import handlers, menu

    for r in (handlers.router, menu.router):  # module-level routers: detach from the previous test's dispatcher
        r._parent_router = None
    _, dp = handlers.create_bot()
    session = RecordingSession()
    bot = Bot(BOT_TOKEN, session=session)
    return lambda tg_id: Chat_(dp, bot, session, tg_id)


async def marker(db, name):
    async with db.SessionLocal() as s:
        return (await s.execute(select(IgxMarker).where(IgxMarker.name == name))).scalar()


async def test_start_explains_bot_and_shows_menu(bot_chat, seeded):
    chat = await bot_chat(555001).say("/start")
    joined = "\n".join(chat.texts)
    assert "PathoUz" in joined and "yo'riqnoma" in joined.lower() and "Asosiy menyu" in joined
    # A new user is a resident: atlas and academy, but no staff sections.
    data = set(chat.buttons().values())
    assert {"at:ask", "ac:home", "m:guide"} <= data and "inv:home" not in data and "ad:home" not in data
    async with seeded.SessionLocal() as s:
        assert (await s.execute(select(User.role).where(User.telegram_id == 555001))).scalar() == Role.RESIDENT

    await chat.press("inv:home")  # typed callback from an old message is still role-checked
    assert chat.alerts and "⛔" in chat.alerts[0]


async def test_technician_receives_lot_and_writes_off(bot_chat, make_user, seeded):
    tech, _ = await make_user(Role.TECHNICIAN)
    chat = bot_chat(tech.telegram_id)
    gab1 = await marker(seeded, "GAB1")
    assert gab1.stock == 0

    await chat.press("inv:home")
    assert "IGX" in chat.texts[0]
    await chat.press(f"inv:m:{gab1.id}")
    assert "GAB1" in chat.texts[0] and f"inv:lot:{gab1.id}" in chat.buttons().values()

    await chat.press(f"inv:lot:{gab1.id}")
    await chat.say("GAB-2026-01")
    await chat.say("01.01.2000")
    assert "noto'g'ri" in chat.texts[0]  # past date is refused, the form waits for a valid one
    await chat.say("31.12.2030")
    await chat.say("abc")
    assert "son" in chat.texts[0]
    await chat.say("25")
    assert any("qabul qilindi" in x for x in chat.texts)
    assert (await marker(seeded, "GAB1")).stock == 25

    async with seeded.SessionLocal() as s:
        lot = (await s.execute(select(IgxLot).where(IgxLot.marker_id == gab1.id))).scalar()
        assert lot.expiry_date == date(2030, 12, 31) and lot.quantity == 25
    await chat.press(f"inv:wo:{gab1.id}")
    await chat.press(f"inv:wl:{lot.id}")
    await chat.say("30")
    assert "25" in chat.texts[0]  # more than the lot holds
    await chat.say("5")
    assert (await marker(seeded, "GAB1")).stock == 20
    async with seeded.SessionLocal() as s:
        moves = (await s.execute(select(StockMovement.reason, StockMovement.delta)
                                 .where(StockMovement.marker_id == gab1.id))).all()
    assert sorted(moves) == [("receive", 25), ("write_off", -5)]


async def test_marker_search_and_pathologist_cannot_receive(bot_chat, make_user, seeded):
    doctor, _ = await make_user(Role.PATHOLOGIST)
    chat = bot_chat(doctor.telegram_id)
    await chat.press("inv:find")
    await chat.say("ki67")
    assert "Ki-67" in chat.texts[0]
    assert not any(v and v.startswith("inv:lot:") for v in chat.buttons().values())
    ki = await marker(seeded, "Ki-67")
    await chat.press(f"inv:lot:{ki.id}")
    assert chat.alerts


async def test_pathologist_registers_biopsy_with_panel_and_approves(bot_chat, make_user, seeded):
    doctor, _ = await make_user(Role.PATHOLOGIST)
    chat = bot_chat(doctor.telegram_id)
    await chat.press("bx:new")
    await chat.press("bx:o:breast")
    await chat.say("Karimova Dilnoza")
    await chat.say("200")
    assert "130" in chat.texts[0]
    await chat.say("47")
    await chat.press("bx:sex:F")
    await chat.say("Chap ko'krak bezida tugun")
    panel = chat.buttons()
    assert any("ER" in k and k.startswith("✅") for k in panel)
    toggle_pr = next(v for k, v in panel.items() if k.endswith(" PR"))
    await chat.press(toggle_pr)  # remove PR
    await chat.say("GAB1")       # typed marker is added
    await chat.press("bx:ok")
    assert any("Biopsiya yaratildi" in x for x in chat.texts)

    async with seeded.SessionLocal() as s:
        b = (await s.execute(select(Biopsy).order_by(Biopsy.id.desc()))).scalars().first()
    names = [m["name"] for m in b.selected_markers]
    assert b.patient_name == "Karimova Dilnoza" and b.patient_age == 47 and b.patient_sex == "F"
    assert "ER" in names and "PR" not in names and "GAB1" in names and b.organ == "breast"

    await chat.press(f"bx:v:{b.code}")
    assert "Karimova" in chat.texts[0] and f"approve:{b.code}" in chat.buttons().values()

    tech, _ = await make_user(Role.TECHNICIAN)
    tchat = bot_chat(tech.telegram_id)
    await tchat.press(f"bx:v:{b.code}")
    assert "Karimova" not in tchat.texts[0] and "K. D." in tchat.texts[0]  # technicians see initials only
    assert f"approve:{b.code}" not in tchat.buttons().values()


async def test_admin_changes_roles_but_not_own(bot_chat, make_user, seeded):
    admin, _ = await make_user(Role.SUPER_ADMIN)
    resident, _ = await make_user(Role.RESIDENT)
    chat = bot_chat(admin.telegram_id)
    await chat.press("ad:l:0")
    assert f"ad:u:{resident.id}" in chat.buttons().values()
    await chat.press(f"ad:r:{resident.id}:technician")
    await chat.press(f"ad:r:{admin.id}:resident")
    assert chat.alerts
    await chat.press(f"ad:b:{resident.id}")
    async with seeded.SessionLocal() as s:
        r = await s.get(User, resident.id)
        a = await s.get(User, admin.id)
    assert r.role == Role.TECHNICIAN and not r.is_active and a.role == Role.SUPER_ADMIN

    other = bot_chat(resident.telegram_id + 100000)
    await other.press(f"ad:r:{resident.id}:super_admin")
    assert other.alerts


async def test_atlas_and_daily_quiz(bot_chat, make_user, seeded):
    student, _ = await make_user(Role.RESIDENT)
    chat = bot_chat(student.telegram_id)
    await chat.press("at:ask")
    await chat.say("melanoma")
    results = [v for v in chat.buttons().values() if v and v.startswith("at:d:")]
    assert results
    await chat.press(results[0])
    assert "IHC" in chat.texts[0]

    await chat.press("ac:home")
    await chat.press("ac:q:0")
    assert "Savol 1/" in chat.texts[0]
    await chat.press("ac:x:0:0")
    assert "To'g'ri" in chat.texts[0] or "Noto'g'ri" in chat.texts[0]
    async with seeded.SessionLocal() as s:
        assert (await s.execute(select(QuizAttempt).where(QuizAttempt.user_id == student.id))).scalar()


async def test_language_switch_and_free_text_returns_menu(bot_chat, make_user, seeded):
    user, _ = await make_user(Role.RESIDENT)
    chat = bot_chat(user.telegram_id)
    await chat.press("m:lang")
    assert "Главное меню" in chat.texts[0]
    await chat.say("salom")
    assert "Главное меню" in chat.texts[0]
