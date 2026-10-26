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
