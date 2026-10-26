"""Bot message strings (UZ / RU)."""

TEXTS = {
    "uz": {
        "welcome": "Assalomu alaykum, {name}! 👋\n\n<b>PathoUz</b> — LIS, IGX inventar va Smart Academy.\nRolingiz: <b>{role}</b>",
        "open_app": "🔬 PathoUz'ni ochish",
        "login_link": "🔐 Brauzerda kirish uchun bir martalik havola (10 daqiqa amal qiladi):\n{url}",
        "login_no_url": "WEBAPP_URL sozlanmagan.",
        "new_biopsy": "🆕 <b>Yangi biopsiya</b> <code>{code}</code>\n📍 {organ}\n🧪 Panel: {markers}",
        "approve_btn": "✅ Panelni tasdiqlash",
        "open_case": "📖 Ochish",
        "approved": "✅ <code>{code}</code> paneli tasdiqlandi ({by}).\nInventardan yechildi: {items}",
        "already": "ℹ️ <code>{code}</code> allaqachon tasdiqlangan.",
        "no_markers": "⚠️ <code>{code}</code> panelida marker yo'q.",
        "shortage": "🔴 <b>Zaxira yetarli emas</b> — <code>{code}</code>\nYetishmaydi: {markers}",
        "low_stock": "🟡 Kam qoldi: {items}",
        "expiring": "⏰ <b>Muddati tugayotgan markerlar</b> (&lt;60 kun):\n{items}",
        "consilium": "💬 <b>Konsilium</b> ochildi: <code>{code}</code> ({by})",
        "forbidden": "⛔ Bu amal uchun huquqingiz yo'q.",
        "not_found": "Topilmadi.",
        "help": "/start — ilovani ochish\n/login — brauzer uchun kirish havolasi\n/inventar — inventar holati\n/til — tilni almashtirish",
        "inventory": "📦 <b>Inventar</b>\nJami: {total}\n🔴 Muddati yaqin: {expiring}\n🟣 Sekin sarflanadigan: {slow}\n🟢 Tez sarflanadigan: {fast}\n⚠️ Kam qolgan: {low_stock}\n⛔ Tugagan: {out_of_stock}",
        "lang_set": "Til: O'zbekcha 🇺🇿",
        "roles": {"super_admin": "👑 Super Admin", "pathologist": "👨‍⚕️ Patolog", "technician": "🧪 Laborant", "resident": "🎓 Rezident / Talaba"},
    },
    "ru": {
        "welcome": "Здравствуйте, {name}! 👋\n\n<b>PathoUz</b> — ЛИС, учёт IGX и Smart Academy.\nВаша роль: <b>{role}</b>",
        "open_app": "🔬 Открыть PathoUz",
        "login_link": "🔐 Одноразовая ссылка для входа в браузере (действует 10 минут):\n{url}",
        "login_no_url": "WEBAPP_URL не настроен.",
        "new_biopsy": "🆕 <b>Новая биопсия</b> <code>{code}</code>\n📍 {organ}\n🧪 Панель: {markers}",
        "approve_btn": "✅ Утвердить панель",
        "open_case": "📖 Открыть",
        "approved": "✅ Панель <code>{code}</code> утверждена ({by}).\nСписано: {items}",
        "already": "ℹ️ <code>{code}</code> уже утверждена.",
        "no_markers": "⚠️ В панели <code>{code}</code> нет маркеров.",
        "shortage": "🔴 <b>Недостаточно реагентов</b> — <code>{code}</code>\nНе хватает: {markers}",
        "low_stock": "🟡 Заканчивается: {items}",
        "expiring": "⏰ <b>Маркеры с истекающим сроком</b> (&lt;60 дней):\n{items}",
        "consilium": "💬 Открыт <b>консилиум</b>: <code>{code}</code> ({by})",
        "forbidden": "⛔ Недостаточно прав.",
        "not_found": "Не найдено.",
        "help": "/start — открыть приложение\n/login — ссылка для входа в браузере\n/inventar — состояние склада\n/til — сменить язык",
        "inventory": "📦 <b>Склад</b>\nВсего: {total}\n🔴 Истекает срок: {expiring}\n🟣 Медленный расход: {slow}\n🟢 Быстрый расход: {fast}\n⚠️ Мало: {low_stock}\n⛔ Нет в наличии: {out_of_stock}",
        "lang_set": "Язык: Русский 🇷🇺",
        "roles": {"super_admin": "👑 Супер-админ", "pathologist": "👨‍⚕️ Патолог", "technician": "🧪 Лаборант", "resident": "🎓 Резидент / Студент"},
    },
}


def t(lang: str, key: str, **kw) -> str:
    table = TEXTS.get(lang) or TEXTS["uz"]
    return table[key].format(**kw) if kw else table[key]


# ---------------------------------------------------------------- in-bot menu (buttons)

TEXTS["uz"].update({
    "about": (
        "🔬 <b>PathoUz — patomorfologiya laboratoriyasi uchun yagona tizim</b>\n\n"
        "Bot va ilova bitta bazada ishlaydi: bu yerda qilgan ishingiz ilovada ham ko'rinadi.\n\n"
        "<b>Nimalar bor:</b>\n"
        "🧫 <b>Biopsiyalar</b> — holatni ro'yxatga olish, IHC panelini tanlash, tasdiqlash (tasdiqlanganda har bir markerdan 1 test avtomatik yechiladi)\n"
        "🧪 <b>IGX Ombor</b> — markerlar qoldig'i, lot qabul qilish, hisobdan chiqarish, muddati yaqinlar\n"
        "📊 <b>Sarf statistikasi</b> — 30 kunlik sarf va eng ko'p ishlatilgan markerlar\n"
        "📚 <b>Atlas</b> — kasalliklar bo'yicha qisqa ma'lumot va IHC profili\n"
        "🎓 <b>Ta'lim</b> — kunlik viktorina va Anki kartalari\n"
        "👑 <b>Admin</b> — xodimlar va rollar (faqat Super Admin)\n\n"
        "Rolingiz: <b>{role}</b>"
    ),
    "guide": (
        "📖 <b>Foydalanish yo'riqnomasi</b>\n\n"
        "<b>1. Boshlash.</b> /start yoki /menu — asosiy menyu. Hamma ish tugmalar orqali bajariladi; matn kerak bo'lsa, bot o'zi so'raydi. Bekor qilish: /cancel.\n\n"
        "<b>2. Yangi biopsiya</b> (patolog, laborant): 🧫 Biopsiyalar → ➕ Yangi → a'zoni tanlang → bemor ismi → yoshi → jinsi → klinik taxmin → panel. A'zoga mos asosiy markerlar avtomatik belgilanadi, Smart Tandem qo'shimcha markerlarni taklif qiladi. ✅ Yaratish ni bosing — patologlarga xabar boradi.\n\n"
        "<b>3. Panelni tasdiqlash</b> (patolog): holat kartasida ✅ Tasdiqlash. Har bir markerdan 1 test eng erta tugaydigan lotdan (FEFO) yechiladi. Zaxira yetmasa, laborantlarga xabar boradi.\n\n"
        "<b>4. Ombor</b> (laborant): 🧪 IGX Ombor → marker → ➕ Lot qabul qilish: lot raqami, yaroqlilik muddati (masalan 31.12.2027) va testlar soni. ➖ Hisobdan chiqarish — singan, muddati o'tgan flakonlar uchun. Har kuni ertalab muddati yaqin markerlar ro'yxati keladi.\n\n"
        "<b>5. Atlas</b>: 📚 Atlas → kasallik nomi, ICD kodi yoki marker yozing.\n\n"
        "<b>6. Ta'lim</b>: 🎯 kunlik viktorina (har kuni 5 savol), 🃏 Anki takrorlash (kartalarni ilovada yaratasiz).\n\n"
        "<b>7. Ilova</b>: 🔬 tugmasi to'liq ilovani ochadi — hisobot yozish, skoring (Allred, HER2, Ki-67), konsilium, galereya, kitoblar. Kompyuterda kirish uchun 🔐 Brauzer havolasi.\n\n"
        "<b>Rollar:</b> yangi foydalanuvchi 🎓 Rezident bo'lib kiradi. Rolni Super Admin beradi (👑 Admin → Xodimlar)."
    ),
    "menu_title": "📋 <b>Asosiy menyu</b>\nRolingiz: {role}",
    "btn_biopsies": "🧫 Biopsiyalar", "btn_inventory": "🧪 IGX Ombor", "btn_stats": "📊 Sarf statistikasi",
    "btn_atlas": "📚 Atlas", "btn_academy": "🎓 Ta'lim", "btn_admin": "👑 Admin", "btn_guide": "📖 Yo'riqnoma",
    "btn_lang": "🌐 Русский", "btn_login": "🔐 Brauzer havolasi", "btn_menu": "🏠 Menyu", "btn_back": "⬅️ Orqaga",
    "btn_more": "Keyingi ▶️", "btn_prev": "◀️ Oldingi", "btn_cancel": "✖️ Bekor qilish", "btn_skip": "⏭ O'tkazib yuborish",
    "cancelled": "Bekor qilindi.", "use_buttons": "Tugmalardan foydalaning yoki /menu.",
    "empty": "Hozircha bo'sh.",
    # inventory
    "inv_title": "🧪 <b>IGX Ombor</b>\nJami markerlar: {total} · jami testlar: {tests}\n🔴 Muddati yaqin: {expiring}\n⚠️ Kam qolgan: {low_stock}\n⛔ Tugagan: {out_of_stock}",
    "btn_inv_all": "📋 Hammasi", "btn_inv_expiring": "🔴 Muddati yaqin", "btn_inv_low": "⚠️ Kam qolgan",
    "btn_inv_out": "⛔ Tugagan", "btn_inv_find": "🔍 Qidirish",
    "inv_list": "🧪 <b>{title}</b> ({n})\nMarkerni tanlang:",
    "inv_find_ask": "🔍 Marker nomini yozing (masalan: CD20, ki67):",
    "inv_found_none": "«{q}» bo'yicha marker topilmadi.",
    "marker_card": "🧪 <b>{name}</b>\n{desc}\n\n📦 Qoldiq: <b>{stock}</b> test\n⏳ Eng yaqin muddat: {expiry}\n📉 30 kunda sarf: {used}\n📍 Bo'yalish joyi: {loc}{lots}",
    "lots_head": "\n\n<b>Lotlar:</b>",
    "lot_line": "\n• {lot} — {expiry} — {qty} test{flag}",
    "lot_expired": " ⛔ muddati o'tgan",
    "btn_lot_add": "➕ Lot qabul qilish", "btn_write_off": "➖ Hisobdan chiqarish", "btn_open_app_inv": "🔬 Ilovada ochish",
    "lot_ask_number": "➕ <b>{name}</b> — yangi lot\n\n1/3. Lot raqamini yozing:",
    "lot_ask_expiry": "2/3. Yaroqlilik muddatini yozing (masalan: 31.12.2027):",
    "lot_bad_date": "Sana noto'g'ri yoki o'tib ketgan. Masalan: 31.12.2027",
    "lot_ask_qty": "3/3. Nechta test (son):",
    "bad_number": "Musbat butun son yozing.",
    "lot_added": "✅ <b>{name}</b>: lot {lot} qabul qilindi ({qty} test, muddati {expiry}).\nJami qoldiq: {stock}",
    "wo_pick_lot": "➖ <b>{name}</b> — qaysi lotdan?",
    "wo_ask_qty": "➖ <b>{name}</b>, lot {lot} (qoldiq {qty}).\nNechta test hisobdan chiqarilsin?",
    "wo_too_many": "Lotda faqat {qty} test bor.",
    "wo_done": "✅ <b>{name}</b>: {n} test hisobdan chiqarildi. Qoldiq: {stock}",
    "no_lots": "Bu markerda faol lot yo'q.",
    # stats
    "stats": "📊 <b>Sarf statistikasi (30 kun)</b>\nJami: <b>{total}</b> test\nMuddati o'tgan, javonda qolgan: {expired} test\n\n<b>Eng ko'p sarflangan:</b>\n{top}\n\n<b>Tez tugaydiganlar (kunga yetadi):</b>\n{cover}",
    # biopsies
    "bx_title": "🧫 <b>Biopsiyalar</b>\nYangi (tasdiq kutmoqda): {registered}\nTasdiqlangan: {approved}\nYakunlangan: {reported}",
    "btn_bx_new": "➕ Yangi biopsiya", "btn_bx_registered": "🕓 Tasdiq kutayotganlar", "btn_bx_recent": "📋 Oxirgilar",
    "bx_list": "🧫 <b>{title}</b>\nHolatni tanlang:",
    "bx_card": "🧫 <b>{code}</b> — {status}\n👤 {patient}\n📍 {organ}\n🩺 {suspicion}\n🧪 Panel: {panel}\n📅 {date}",
    "btn_report": "📄 Hisobot (chop etish)", "btn_labels": "🏷 Stikerlar",
    "print_link": "🖨 Havola 5 daqiqa amal qiladi, brauzerda oching:\n{url}",
    "bx_ask_organ": "➕ <b>Yangi biopsiya</b>\n\n1/5. A'zoni tanlang:",
    "bx_ask_name": "2/5. Bemorning F.I.Sh.:",
    "bx_bad_name": "Kamida 2 ta harf yozing.",
    "bx_ask_age": "3/5. Yoshi (son) yoki o'tkazib yuboring:",
    "bx_bad_age": "0 dan 130 gacha son yozing.",
    "bx_ask_sex": "4/5. Jinsi:", "btn_male": "👨 Erkak", "btn_female": "👩 Ayol",
    "bx_ask_susp": "5/5. Klinik taxmin (qisqa) yoki o'tkazib yuboring:",
    "bx_panel": "🧪 <b>IHC paneli</b> — {organ}\nBelgilanganlar: {selected}\n\nMarkerni bosib qo'shing yoki olib tashlang. ✨ — Smart Tandem taklifi.\nBoshqa markerni qo'shish uchun nomini yozing.",
    "btn_create": "✅ Yaratish",
    "bx_created": "✅ Biopsiya yaratildi: <b>{code}</b>\nPanel: {panel}\nPatologlarga xabar yuborildi.",
    "bx_need_marker": "Kamida bitta marker tanlang.",
    "status": {"registered": "🕓 tasdiq kutmoqda", "approved": "✅ tasdiqlangan", "reported": "📄 yakunlangan"},
    # atlas
    "atlas_ask": "📚 <b>Atlas</b>\nKasallik nomi, ICD-10 kodi yoki marker yozing (masalan: melanoma, C34, TTF-1):",
    "atlas_none": "«{q}» bo'yicha hech narsa topilmadi. Boshqacha yozib ko'ring.",
    "atlas_found": "📚 «{q}» — {n} ta natija:",
    "atlas_card": "📚 <b>{name}</b>\n<i>{name_en}</i> · {icd}\n📍 {organ}\n\n{definition}\n\n<b>IHC:</b> {markers}",
    "btn_atlas_again": "🔍 Yana qidirish", "btn_open_disease": "🔬 Ilovada to'liq ochish",
    # academy
    "academy": "🎓 <b>Ta'lim</b>\n🎯 Bugungi viktorina: {done}/{total} javob berilgan\n🃏 Anki: takrorlashga {due} ta karta (jami {cards})\n📈 Umumiy natija: {correct}/{answered} to'g'ri",
    "btn_quiz": "🎯 Kunlik viktorina", "btn_anki": "🃏 Anki takrorlash", "btn_open_academy": "📖 Kitoblar (ilovada)",
    "quiz_q": "🎯 <b>Savol {i}/{n}</b>\n\n{text}\n\n{options}",
    "quiz_right": "✅ <b>To'g'ri!</b>", "quiz_wrong": "❌ <b>Noto'g'ri.</b> To'g'ri javob: {letter}",
    "quiz_done": "🎉 Bugungi viktorina tugadi: {correct}/{n} to'g'ri.\nErtaga yangi savollar.",
    "btn_next": "Keyingi ➡️",
    "anki_none": "🃏 Bugun takrorlash uchun karta yo'q. Kartalarni ilovada (Ta'lim → Kitoblar yoki Anki) yaratasiz.",
    "anki_front": "🃏 <b>Karta</b> ({left} ta qoldi)\n\n{front}",
    "anki_back": "🃏 {front}\n\n━━━━━━━━\n{back}\n\nQanchalik oson esladingiz?",
    "btn_show": "👁 Javobni ko'rsatish",
    "btn_again": "🔁 Qayta", "btn_hard": "😓 Qiyin", "btn_good": "🙂 Yaxshi", "btn_easy": "😎 Oson",
    # admin
    "admin": "👑 <b>Admin</b>\nFoydalanuvchilar: {users} (faol: {active})\nBiopsiyalar: {biopsies}",
    "btn_users": "👥 Xodimlar va rollar",
    "users_list": "👥 <b>Xodimlar</b> — rolni o'zgartirish uchun tanlang:",
    "user_card": "👤 <b>{name}</b>{username}\nRol: {role}\nHolat: {state}\nTasdiqlagan holatlari: {cases}",
    "state_active": "✅ faol", "state_blocked": "⛔ bloklangan",
    "btn_block": "⛔ Bloklash", "btn_unblock": "✅ Faollashtirish",
    "self_change": "O'zingizning rolingizni o'zgartira yoki bloklay olmaysiz.",
    "user_updated": "✅ Saqlandi.",
})

TEXTS["ru"].update({
    "about": (
        "🔬 <b>PathoUz — единая система для лаборатории патоморфологии</b>\n\n"
        "Бот и приложение работают с одной базой: всё, что вы делаете здесь, видно и в приложении.\n\n"
        "<b>Что есть:</b>\n"
        "🧫 <b>Биопсии</b> — регистрация случая, выбор ИГХ-панели, утверждение (при утверждении с каждого маркера автоматически списывается 1 тест)\n"
        "🧪 <b>Склад IGX</b> — остатки маркеров, приём лотов, списание, истекающие сроки\n"
        "📊 <b>Статистика расхода</b> — расход за 30 дней и самые используемые маркеры\n"
        "📚 <b>Атлас</b> — краткие сведения о заболеваниях и ИГХ-профиль\n"
        "🎓 <b>Обучение</b> — ежедневная викторина и карточки Anki\n"
        "👑 <b>Админ</b> — сотрудники и роли (только Супер-админ)\n\n"
        "Ваша роль: <b>{role}</b>"
    ),
    "guide": (
        "📖 <b>Инструкция</b>\n\n"
        "<b>1. Начало.</b> /start или /menu — главное меню. Всё делается кнопками; если нужен текст, бот сам попросит. Отмена: /cancel.\n\n"
        "<b>2. Новая биопсия</b> (патолог, лаборант): 🧫 Биопсии → ➕ Новая → выберите орган → ФИО пациента → возраст → пол → клинический диагноз → панель. Базовые маркеры для органа отмечаются автоматически, Smart Tandem предлагает дополнительные. Нажмите ✅ Создать — патологи получат уведомление.\n\n"
        "<b>3. Утверждение панели</b> (патолог): в карточке случая ✅ Утвердить. С каждого маркера списывается 1 тест из лота с ближайшим сроком (FEFO). Если реагента не хватает, лаборанты получат уведомление.\n\n"
        "<b>4. Склад</b> (лаборант): 🧪 Склад IGX → маркер → ➕ Принять лот: номер лота, срок годности (например 31.12.2027) и число тестов. ➖ Списать — для разбитых или просроченных флаконов. Каждое утро приходит список маркеров с истекающим сроком.\n\n"
        "<b>5. Атлас</b>: 📚 Атлас → напишите название болезни, код МКБ или маркер.\n\n"
        "<b>6. Обучение</b>: 🎯 ежедневная викторина (5 вопросов в день), 🃏 повторение Anki (карточки создаются в приложении).\n\n"
        "<b>7. Приложение</b>: кнопка 🔬 открывает полное приложение — заключения, скоринг (Allred, HER2, Ki-67), консилиум, галерея, книги. Для входа с компьютера — 🔐 Ссылка для браузера.\n\n"
        "<b>Роли:</b> новый пользователь входит как 🎓 Резидент. Роль назначает Супер-админ (👑 Админ → Сотрудники)."
    ),
    "menu_title": "📋 <b>Главное меню</b>\nВаша роль: {role}",
    "btn_biopsies": "🧫 Биопсии", "btn_inventory": "🧪 Склад IGX", "btn_stats": "📊 Статистика расхода",
    "btn_atlas": "📚 Атлас", "btn_academy": "🎓 Обучение", "btn_admin": "👑 Админ", "btn_guide": "📖 Инструкция",
    "btn_lang": "🌐 O'zbekcha", "btn_login": "🔐 Ссылка для браузера", "btn_menu": "🏠 Меню", "btn_back": "⬅️ Назад",
    "btn_more": "Далее ▶️", "btn_prev": "◀️ Назад", "btn_cancel": "✖️ Отмена", "btn_skip": "⏭ Пропустить",
    "cancelled": "Отменено.", "use_buttons": "Пользуйтесь кнопками или /menu.",
    "empty": "Пока пусто.",
    "inv_title": "🧪 <b>Склад IGX</b>\nВсего маркеров: {total} · всего тестов: {tests}\n🔴 Истекает срок: {expiring}\n⚠️ Мало: {low_stock}\n⛔ Нет в наличии: {out_of_stock}",
    "btn_inv_all": "📋 Все", "btn_inv_expiring": "🔴 Истекает срок", "btn_inv_low": "⚠️ Мало",
    "btn_inv_out": "⛔ Нет в наличии", "btn_inv_find": "🔍 Поиск",
    "inv_list": "🧪 <b>{title}</b> ({n})\nВыберите маркер:",
    "inv_find_ask": "🔍 Напишите название маркера (например: CD20, ki67):",
    "inv_found_none": "Маркер «{q}» не найден.",
    "marker_card": "🧪 <b>{name}</b>\n{desc}\n\n📦 Остаток: <b>{stock}</b> тестов\n⏳ Ближайший срок: {expiry}\n📉 Расход за 30 дней: {used}\n📍 Локализация: {loc}{lots}",
    "lots_head": "\n\n<b>Лоты:</b>",
    "lot_line": "\n• {lot} — {expiry} — {qty} тестов{flag}",
    "lot_expired": " ⛔ просрочен",
    "btn_lot_add": "➕ Принять лот", "btn_write_off": "➖ Списать", "btn_open_app_inv": "🔬 Открыть в приложении",
    "lot_ask_number": "➕ <b>{name}</b> — новый лот\n\n1/3. Напишите номер лота:",
    "lot_ask_expiry": "2/3. Срок годности (например: 31.12.2027):",
    "lot_bad_date": "Неверная или прошедшая дата. Например: 31.12.2027",
    "lot_ask_qty": "3/3. Сколько тестов (число):",
    "bad_number": "Напишите целое положительное число.",
    "lot_added": "✅ <b>{name}</b>: принят лот {lot} ({qty} тестов, срок {expiry}).\nОбщий остаток: {stock}",
    "wo_pick_lot": "➖ <b>{name}</b> — из какого лота?",
    "wo_ask_qty": "➖ <b>{name}</b>, лот {lot} (остаток {qty}).\nСколько тестов списать?",
    "wo_too_many": "В лоте только {qty} тестов.",
    "wo_done": "✅ <b>{name}</b>: списано {n} тестов. Остаток: {stock}",
    "no_lots": "У маркера нет активных лотов.",
    "stats": "📊 <b>Статистика расхода (30 дней)</b>\nВсего: <b>{total}</b> тестов\nПросрочено и осталось на полке: {expired} тестов\n\n<b>Больше всего израсходовано:</b>\n{top}\n\n<b>Скоро закончатся (хватит на дней):</b>\n{cover}",
    "bx_title": "🧫 <b>Биопсии</b>\nНовые (ждут утверждения): {registered}\nУтверждены: {approved}\nЗавершены: {reported}",
    "btn_bx_new": "➕ Новая биопсия", "btn_bx_registered": "🕓 Ждут утверждения", "btn_bx_recent": "📋 Последние",
    "bx_list": "🧫 <b>{title}</b>\nВыберите случай:",
    "bx_card": "🧫 <b>{code}</b> — {status}\n👤 {patient}\n📍 {organ}\n🩺 {suspicion}\n🧪 Панель: {panel}\n📅 {date}",
    "btn_report": "📄 Заключение (печать)", "btn_labels": "🏷 Наклейки",
    "print_link": "🖨 Ссылка действует 5 минут, откройте в браузере:\n{url}",
    "bx_ask_organ": "➕ <b>Новая биопсия</b>\n\n1/5. Выберите орган:",
    "bx_ask_name": "2/5. ФИО пациента:",
    "bx_bad_name": "Минимум 2 буквы.",
    "bx_ask_age": "3/5. Возраст (число) или пропустите:",
    "bx_bad_age": "Число от 0 до 130.",
    "bx_ask_sex": "4/5. Пол:", "btn_male": "👨 Муж.", "btn_female": "👩 Жен.",
    "bx_ask_susp": "5/5. Клинический диагноз (кратко) или пропустите:",
    "bx_panel": "🧪 <b>ИГХ-панель</b> — {organ}\nВыбрано: {selected}\n\nНажмите на маркер, чтобы добавить или убрать. ✨ — предложение Smart Tandem.\nЧтобы добавить другой маркер, напишите его название.",
    "btn_create": "✅ Создать",
    "bx_created": "✅ Биопсия создана: <b>{code}</b>\nПанель: {panel}\nПатологи получили уведомление.",
    "bx_need_marker": "Выберите хотя бы один маркер.",
    "status": {"registered": "🕓 ждёт утверждения", "approved": "✅ утверждена", "reported": "📄 завершена"},
    "atlas_ask": "📚 <b>Атлас</b>\nНапишите название болезни, код МКБ-10 или маркер (например: меланома, C34, TTF-1):",
    "atlas_none": "По запросу «{q}» ничего не найдено. Попробуйте иначе.",
    "atlas_found": "📚 «{q}» — найдено: {n}",
    "atlas_card": "📚 <b>{name}</b>\n<i>{name_en}</i> · {icd}\n📍 {organ}\n\n{definition}\n\n<b>ИГХ:</b> {markers}",
    "btn_atlas_again": "🔍 Искать ещё", "btn_open_disease": "🔬 Открыть полностью",
    "academy": "🎓 <b>Обучение</b>\n🎯 Викторина сегодня: отвечено {done}/{total}\n🃏 Anki: к повторению {due} (всего {cards})\n📈 Общий результат: {correct}/{answered} верно",
    "btn_quiz": "🎯 Ежедневная викторина", "btn_anki": "🃏 Повторение Anki", "btn_open_academy": "📖 Книги (в приложении)",
    "quiz_q": "🎯 <b>Вопрос {i}/{n}</b>\n\n{text}\n\n{options}",
    "quiz_right": "✅ <b>Верно!</b>", "quiz_wrong": "❌ <b>Неверно.</b> Правильный ответ: {letter}",
    "quiz_done": "🎉 Викторина на сегодня завершена: {correct}/{n} верно.\nЗавтра — новые вопросы.",
    "btn_next": "Далее ➡️",
    "anki_none": "🃏 На сегодня карточек для повторения нет. Карточки создаются в приложении (Обучение → Книги или Anki).",
    "anki_front": "🃏 <b>Карточка</b> (осталось {left})\n\n{front}",
    "anki_back": "🃏 {front}\n\n━━━━━━━━\n{back}\n\nНасколько легко вспомнили?",
    "btn_show": "👁 Показать ответ",
    "btn_again": "🔁 Снова", "btn_hard": "😓 Трудно", "btn_good": "🙂 Хорошо", "btn_easy": "😎 Легко",
    "admin": "👑 <b>Админ</b>\nПользователи: {users} (активны: {active})\nБиопсии: {biopsies}",
    "btn_users": "👥 Сотрудники и роли",
    "users_list": "👥 <b>Сотрудники</b> — выберите, чтобы изменить роль:",
    "user_card": "👤 <b>{name}</b>{username}\nРоль: {role}\nСтатус: {state}\nУтверждено случаев: {cases}",
    "state_active": "✅ активен", "state_blocked": "⛔ заблокирован",
    "btn_block": "⛔ Заблокировать", "btn_unblock": "✅ Разблокировать",
    "self_change": "Нельзя изменить роль или заблокировать себя.",
    "user_updated": "✅ Сохранено.",
})

for _lang in TEXTS.values():
    _lang["help"] = "/start — ma'lumot va yo'riqnoma\n/menu — asosiy menyu\n/login — brauzer uchun kirish havolasi\n/til — tilni almashtirish\n/cancel — amalni bekor qilish" \
        if _lang is TEXTS["uz"] else \
        "/start — о боте и инструкция\n/menu — главное меню\n/login — ссылка для входа в браузере\n/til — сменить язык\n/cancel — отменить действие"
