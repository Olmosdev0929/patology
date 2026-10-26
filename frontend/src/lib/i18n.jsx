import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { STRINGS } from "./strings";

const DICT = {
  uz: {
    app: { tagline: "LIS · IGX Inventar · Smart Academy" },
    nav: { dashboard: "Panel", atlas: "Atlas", cases: "Biopsiyalar", inventory: "Inventar", academy: "Akademiya", admin: "Admin" },
    roles: { super_admin: "👑 Super Admin", pathologist: "👨‍⚕️ Patolog", technician: "🧪 Laborant", resident: "🎓 Rezident / Talaba" },
    common: {
      loading: "Yuklanmoqda…", save: "Saqlash", cancel: "Bekor qilish", close: "Yopish", add: "Qo'shish", search: "Qidirish",
      all: "Barchasi", edit: "Tahrirlash", empty: "Ma'lumot yo'q", error: "Xatolik", back: "Orqaga", yes: "Ha", no: "Yo'q",
      days: "kun", tests: "test", logout: "Chiqish", saved: "Saqlandi", open: "Ochish", retry: "Qayta urinish",
    },
    login: {
      title: "PathoUz'ga kirish", telegram: "Ilovani Telegram ichida oching yoki botdan /login buyrug'i bilan havola oling.",
      checking: "Kirish tekshirilmoqda…", failed: "Kirish amalga oshmadi", dev: "Dev rejimida kirish", openBot: "Botni ochish",
    },
    dash: {
      hello: "Salom, {name}", todayQueue: "Bugungi navbat", registered: "Ro'yxatga olingan", approved: "Bo'yalmoqda",
      reported: "Yakunlangan", consilium: "Konsilium", invAlerts: "Inventar ogohlantirishlari", dueCards: "Takrorlash kerak",
      quizToday: "Bugungi viktorina", startQuiz: "Boshlash", recentCases: "So'nggi biopsiyalar", newCase: "Yangi biopsiya",
    },
    status: { registered: "Ro'yxatda", approved: "Tasdiqlangan", reported: "Yakunlangan" },
    tags: {
      expiring: "🔴 Muddati yaqin", slow: "🟣 Sekin sarflanadi", fast: "🟢 Tez sarflanadi",
      low_stock: "🟡 Kam qoldi", out_of_stock: "⛔ Tugagan",
    },
    organs: {
      breast: "Ko'krak bezi", lung: "O'pka", colon: "Yo'g'on ichak", stomach: "Oshqozon", liver: "Jigar", kidney: "Buyrak",
      prostate: "Prostata", thyroid: "Qalqonsimon bez", skin: "Teri", lymph: "Limfa tugunlari", cervix: "Bachadon bo'yni", other: "Boshqa",
    },
    atlas: {
      title: "Kasalliklar atlasi", search: "Kasallik, marker yoki belgi…", topics: "{n} mavzu", markers: "Markerlar paneli",
      gallery: "Galereya", noImages: "Hozircha rasm yo'q", refs: "Manbalar", updated: "Yangilangan",
      sections: {
        definition: "Ta'rif", epidemiology: "Epidemiologiya", clinical: "Klinik belgilar", gross: "Makroskopiya",
        microscopic: "Mikroskopiya", ihc: "IHC va molekulyar", differential: "Differensial diagnoz", prognosis: "Prognoz",
      },
      upload: "Rasm yuklash", disclaimer: "Ta'limiy maqsadda. Klinik qaror uchun yagona manba emas.",
    },
    cases: {
      title: "Biopsiyalar", new: "Yangi biopsiya", searchPh: "Kod yoki bemor…", patient: "Bemor F.I.Sh.", age: "Yosh",
      sex: "Jins", male: "Erkak", female: "Ayol", organ: "A'zo / tizim", suspicion: "Klinik taxmin", initialTests: "Dastlabki testlar",
      routine: "Asosiy markerlar", register: "Ro'yxatga olish", panel: "IHC paneli", noMarkers: "Marker tanlanmagan",
      addMarker: "Marker qo'shish", addPh: "Inventardan qidiring yoki yangi nom yozing…", newCustom: "Yangi marker sifatida qo'shish: «{name}»",
      tandem: "Smart Tandem", tandemHint: "Tanlangan markerlarga klinik jihatdan mos va zaxirada muddati yaqin / kam ishlatilgan markerlar. Faqat klinik ko'rsatma bo'lsa qo'shing.",
      noTandem: "Mos tavsiya yo'q", add: "Qo'shish", approve: "Panelni tasdiqlash (−1 test)", approveConfirm: "Panel tasdiqlanadi va har bir markerdan 1 test yechiladi. Davom etasizmi?",
      approvedMsg: "Tasdiqlandi. Yechildi: {items}", shortage: "Zaxira yetarli emas: {items}", source: { routine: "asosiy", tandem: "tandem", custom: "maxsus" },
      macro: "Makroskopiya", micro: "Mikroskopiya", diagnosis: "Xulosa (diagnoz)", templates: "Shablonlar", scoring: "Skoring",
      openScoring: "Kalkulyatorlar", signOut: "Yakunlash va imzolash", signOutConfirm: "Holat yakunlanadi va tahrirlab bo'lmaydi. Davom etasizmi?",
      consilium: "Konsilium", openConsilium: "Konsiliumga chiqarish", closeConsilium: "Konsiliumni yopish",
      comment: "Fikr yozing: mikroskopik topilmalar, tavsiyalar…", send: "Yuborish", noComments: "Hali fikr yo'q",
      images: "Preparat rasmlari", uploadImage: "Rasm yuklash", created: "Ro'yxatga olingan", stockLeft: "qoldi", remove: "Olib tashlash",
      frozen: "Panel tasdiqlangan — o'zgartirib bo'lmaydi",
    },
    scoring: {
      title: "IHC skoring kalkulyatorlari", allred: "Allred (ER/PR)", percent: "Musbat yadrolar, %", intensity: "Intensivlik",
      int: ["0 — yo'q", "1 — kuchsiz", "2 — o'rtacha", "3 — kuchli"], ps: "Proporsiya bali", is: "Intensivlik bali", total: "Jami",
      cat: { positive: "Musbat", low_positive: "Past musbat (1–10%)", negative: "Manfiy" },
      her2: "HER2/neu (ASCO/CAP)", pattern: "Bo'yalish naqshi", ish: "ISH natijasi",
      ishOpt: { none: "Qilinmagan", amp: "Amplifikatsiya bor", noamp: "Amplifikatsiya yo'q" },
      patterns: {
        none: "Bo'yalish yo'q",
        faint_incomplete_le10: "Kuchsiz, to'liq bo'lmagan, ≤10% hujayra",
        faint_incomplete_gt10: "Kuchsiz, to'liq bo'lmagan, >10% hujayra",
        weak_moderate_complete: "Kuchsiz–o'rtacha to'liq membrana, >10%",
        intense_complete_le10: "Kuchli to'liq membrana, ≤10%",
        intense_complete_gt10: "Kuchli to'liq aylana membrana, >10%",
      },
      her2Status: { positive: "Musbat", equivocal: "Noaniq — ISH (FISH) tavsiya etiladi", low: "HER2-past", ultralow: "HER2-ultrapast", zero: "HER2 0" },
      ki67: "Ki-67 indeksi", cutoff: "Laboratoriya chegarasi, %", high: "Yuqori", low: "Past",
      subtype: "Molekulyar surrogat turi",
      subtypes: {
        luminal_a: "Luminal A", luminal_b_her2_neg: "Luminal B (HER2−)", luminal_b_her2_pos: "Luminal B (HER2+)",
        her2_enriched: "HER2-boyitilgan", triple_negative: "Uch karra manfiy", pending_her2: "HER2 ISH natijasi kutilmoqda",
      },
      save: "Natijani saqlash", note: "Hisob-kitob ASCO/CAP va St Gallen mezonlariga asoslangan. Yakuniy talqin patolog zimmasida.",
    },
    inv: {
      title: "IGX inventar", searchPh: "Marker nomi…", stock: "Zaxira", expiry: "Yaroqlilik", used30: "30 kunda",
      clone: "Klon", passport: "Laboratoriya pasporti", buffer: "Antigen retrieval buferi", retrievalTime: "Qizdirish vaqti",
      dilution: "Birlamchi antitana suyultirish", incubation: "Inkubatsiya", control: "Musbat nazorat to'qimasi",
      localization: "Hujayra ichida joylashuv", notes: "Izoh", verified: "Tekshirilgan", notVerified: "Tekshirilmagan",
      verify: "Pasportni tasdiqlash", lots: "Lotlar (FEFO tartibida)", receive: "Yangi lot qabul qilish", lot: "Lot raqami",
      qty: "Miqdor (test)", expired: "Muddati o'tgan", tandemWith: "Tandem", newMarker: "Yangi marker", name: "Nomi",
      writeOff: "Hisobdan chiqarish", min: "daq", fefoNote: "Yechish eng birinchi muddati tugaydigan yaroqli lotdan amalga oshiriladi.",
      loc: { nuclear: "Yadro", membranous: "Membrana", cytoplasmic: "Sitoplazma" },
    },
    academy: {
      title: "Smart Academy", reader: "Parallel o'quvchi", anki: "Anki kartalari", quiz: "Kunlik viktorina",
      listen: "Tinglash", toCard: "Kartaga", cardAdded: "Karta qo'shildi", terms: "Atamalar", showTranslation: "Tarjima",
      due: "Bugun takrorlash: {n}", total: "Jami kartalar: {n}", mature: "O'zlashtirilgan: {n}", showAnswer: "Javobni ko'rsatish",
      again: "Yana", hard: "Qiyin", good: "Yaxshi", easy: "Oson", noDue: "Bugun uchun takrorlash yo'q 🎉",
      newCard: "Yangi karta", front: "Old tomoni", backSide: "Orqa tomoni", deck: "To'plam",
      correct: "To'g'ri!", wrong: "Noto'g'ri", explanation: "Izoh", next: "Keyingi", score: "Natija: {c}/{n}", done: "Bugungi viktorina yakunlandi",
      license: "Litsenziya", sentences: "{n} gap",
    },
    admin: {
      title: "Boshqaruv", staff: "Xodimlar", kpi: "KPI", audit: "Audit jurnali", role: "Rol", active: "Faol",
      casesDone: "Yakunlangan holatlar", saved: "Qutqarilgan markerlar", panels: "Tasdiqlangan panellar",
      verify: "Zanjirni tekshirish", chainOk: "Audit zanjiri butun ({n} yozuv)", chainBroken: "Diqqat! Zanjir #{id} da buzilgan",
      specialty: "Mutaxassislik",
    },
    audit: {
      "biopsy.create": "Biopsiya ro'yxatga olindi {code}", "biopsy.approve": "Panel tasdiqlandi {code}: −{tests} test",
      "biopsy.update": "Biopsiya tahrirlandi {code}", "biopsy.scoring": "Skoring saqlandi {code}", "biopsy.report": "Yakunlandi {code}",
      "consilium.open": "Konsilium ochildi {code}", "consilium.close": "Konsilium yopildi {code}", "consilium.comment": "Konsiliumga fikr {code}",
      "marker.create": "Marker qo'shildi: {name}", "marker.custom_create": "Maxsus marker qo'shildi: {name}", "marker.update": "Marker tahrirlandi: {name}",
      "marker.passport_verify": "Pasport tasdiqlandi: {name}", "stock.receive": "Lot qabul qilindi: {name} {lot} (+{quantity})",
      "stock.adjust": "Zaxira tuzatildi: {name} ({delta})", "stock.write_off": "Hisobdan chiqarildi: {name} ({delta})",
      "image.upload": "Rasm yuklandi #{id}", "image.pins": "Rasm belgilari #{id}", "user.register": "Yangi foydalanuvchi",
      "user.update": "Foydalanuvchi o'zgartirildi: {user}", "user.web_login": "Brauzer orqali kirish", "atlas.update": "Atlas tahrirlandi: {slug}",
      "book.import": "Kitob import qilindi: {title}",
    },
    img: { kind: "Turi", micro: "Mikroskopik", macro: "Makroskopik", stain: "Bo'yoq", captionUz: "Izoh (UZ)", captionRu: "Izoh (RU)", file: "Fayl", pins: "Belgilar", addPin: "Belgi qo'yish uchun rasmga bosing", pinLabel: "Belgi nomi" },
  },
  ru: {
    app: { tagline: "ЛИС · Склад IGX · Smart Academy" },
    nav: { dashboard: "Панель", atlas: "Атлас", cases: "Биопсии", inventory: "Склад", academy: "Академия", admin: "Админ" },
    roles: { super_admin: "👑 Супер-админ", pathologist: "👨‍⚕️ Патолог", technician: "🧪 Лаборант", resident: "🎓 Резидент / Студент" },
    common: {
      loading: "Загрузка…", save: "Сохранить", cancel: "Отмена", close: "Закрыть", add: "Добавить", search: "Поиск",
      all: "Все", edit: "Изменить", empty: "Нет данных", error: "Ошибка", back: "Назад", yes: "Да", no: "Нет",
      days: "дн.", tests: "тест.", logout: "Выйти", saved: "Сохранено", open: "Открыть", retry: "Повторить",
    },
    login: {
      title: "Вход в PathoUz", telegram: "Откройте приложение внутри Telegram или получите ссылку командой /login в боте.",
      checking: "Проверка входа…", failed: "Не удалось войти", dev: "Вход в dev-режиме", openBot: "Открыть бота",
    },
    dash: {
      hello: "Здравствуйте, {name}", todayQueue: "Очередь", registered: "Зарегистрировано", approved: "Окрашивается",
      reported: "Завершено", consilium: "Консилиум", invAlerts: "Сигналы склада", dueCards: "К повторению",
      quizToday: "Викторина дня", startQuiz: "Начать", recentCases: "Последние биопсии", newCase: "Новая биопсия",
    },
    status: { registered: "Зарегистрирована", approved: "Утверждена", reported: "Завершена" },
    tags: {
      expiring: "🔴 Истекает срок", slow: "🟣 Медленный расход", fast: "🟢 Быстрый расход",
      low_stock: "🟡 Мало", out_of_stock: "⛔ Нет в наличии",
    },
    organs: {
      breast: "Молочная железа", lung: "Лёгкое", colon: "Толстая кишка", stomach: "Желудок", liver: "Печень", kidney: "Почка",
      prostate: "Простата", thyroid: "Щитовидная железа", skin: "Кожа", lymph: "Лимфоузлы", cervix: "Шейка матки", other: "Другое",
    },
    atlas: {
      title: "Атлас заболеваний", search: "Заболевание, маркер или признак…", topics: "{n} тем", markers: "Панель маркеров",
      gallery: "Галерея", noImages: "Изображений пока нет", refs: "Источники", updated: "Обновлено",
      sections: {
        definition: "Определение", epidemiology: "Эпидемиология", clinical: "Клиника", gross: "Макроскопия",
        microscopic: "Микроскопия", ihc: "ИГХ и молекулярные данные", differential: "Дифференциальный диагноз", prognosis: "Прогноз",
      },
      upload: "Загрузить изображение", disclaimer: "В образовательных целях. Не единственный источник для клинических решений.",
    },
    cases: {
      title: "Биопсии", new: "Новая биопсия", searchPh: "Код или пациент…", patient: "Ф.И.О. пациента", age: "Возраст",
      sex: "Пол", male: "Муж.", female: "Жен.", organ: "Орган / система", suspicion: "Клиническое предположение", initialTests: "Первичные тесты",
      routine: "Основные маркеры", register: "Зарегистрировать", panel: "Панель ИГХ", noMarkers: "Маркеры не выбраны",
      addMarker: "Добавить маркер", addPh: "Найдите на складе или введите новое название…", newCustom: "Добавить как новый маркер: «{name}»",
      tandem: "Smart Tandem", tandemHint: "Клинически связанные с выбранными маркеры, у которых истекает срок или низкий расход. Добавляйте только при клиническом показании.",
      noTandem: "Подходящих рекомендаций нет", add: "Добавить", approve: "Утвердить панель (−1 тест)", approveConfirm: "Панель будет утверждена, с каждого маркера списан 1 тест. Продолжить?",
      approvedMsg: "Утверждено. Списано: {items}", shortage: "Недостаточно реагентов: {items}", source: { routine: "основной", tandem: "тандем", custom: "свой" },
      macro: "Макроскопия", micro: "Микроскопия", diagnosis: "Заключение (диагноз)", templates: "Шаблоны", scoring: "Скоринг",
      openScoring: "Калькуляторы", signOut: "Завершить и подписать", signOutConfirm: "Случай будет завершён без возможности редактирования. Продолжить?",
      consilium: "Консилиум", openConsilium: "Вынести на консилиум", closeConsilium: "Закрыть консилиум",
      comment: "Ваше мнение: микроскопические находки, рекомендации…", send: "Отправить", noComments: "Мнений пока нет",
      images: "Изображения препаратов", uploadImage: "Загрузить изображение", created: "Зарегистрирована", stockLeft: "осталось", remove: "Убрать",
      frozen: "Панель утверждена — изменения невозможны",
    },
    scoring: {
      title: "Калькуляторы ИГХ-скоринга", allred: "Allred (ER/PR)", percent: "Позитивные ядра, %", intensity: "Интенсивность",
      int: ["0 — нет", "1 — слабая", "2 — умеренная", "3 — сильная"], ps: "Балл доли", is: "Балл интенсивности", total: "Итого",
      cat: { positive: "Позитивно", low_positive: "Низкопозитивно (1–10%)", negative: "Негативно" },
      her2: "HER2/neu (ASCO/CAP)", pattern: "Тип окрашивания", ish: "Результат ISH",
      ishOpt: { none: "Не проводилось", amp: "Амплификация есть", noamp: "Амплификации нет" },
      patterns: {
        none: "Окрашивания нет",
        faint_incomplete_le10: "Слабое неполное, ≤10% клеток",
        faint_incomplete_gt10: "Слабое неполное, >10% клеток",
        weak_moderate_complete: "Слабое–умеренное полное мембранное, >10%",
        intense_complete_le10: "Интенсивное полное мембранное, ≤10%",
        intense_complete_gt10: "Интенсивное полное циркулярное мембранное, >10%",
      },
      her2Status: { positive: "Позитивный", equivocal: "Сомнительный — рекомендована ISH (FISH)", low: "HER2-low", ultralow: "HER2-ultralow", zero: "HER2 0" },
      ki67: "Индекс Ki-67", cutoff: "Порог лаборатории, %", high: "Высокий", low: "Низкий",
      subtype: "Суррогатный молекулярный подтип",
      subtypes: {
        luminal_a: "Люминальный A", luminal_b_her2_neg: "Люминальный B (HER2−)", luminal_b_her2_pos: "Люминальный B (HER2+)",
        her2_enriched: "HER2-обогащённый", triple_negative: "Тройной негативный", pending_her2: "Ожидается результат HER2 ISH",
      },
      save: "Сохранить результат", note: "Расчёт основан на критериях ASCO/CAP и St Gallen. Окончательная интерпретация — за патологом.",
    },
    inv: {
      title: "Склад IGX", searchPh: "Название маркера…", stock: "Остаток", expiry: "Годен до", used30: "За 30 дней",
      clone: "Клон", passport: "Лабораторный паспорт", buffer: "Буфер демаскировки", retrievalTime: "Время нагрева",
      dilution: "Разведение первичных АТ", incubation: "Инкубация", control: "Положительный контроль",
      localization: "Локализация в клетке", notes: "Примечание", verified: "Проверен", notVerified: "Не проверен",
      verify: "Подтвердить паспорт", lots: "Лоты (порядок FEFO)", receive: "Приём нового лота", lot: "Номер лота",
      qty: "Количество (тестов)", expired: "Просрочен", tandemWith: "Тандем", newMarker: "Новый маркер", name: "Название",
      writeOff: "Списать", min: "мин", fefoNote: "Списание идёт с годного лота с самым ранним сроком годности.",
      loc: { nuclear: "Ядерная", membranous: "Мембранная", cytoplasmic: "Цитоплазматическая" },
    },
    academy: {
      title: "Smart Academy", reader: "Параллельное чтение", anki: "Карточки Anki", quiz: "Викторина дня",
      listen: "Прослушать", toCard: "В карточку", cardAdded: "Карточка добавлена", terms: "Термины", showTranslation: "Перевод",
      due: "К повторению сегодня: {n}", total: "Всего карточек: {n}", mature: "Выучено: {n}", showAnswer: "Показать ответ",
      again: "Снова", hard: "Трудно", good: "Хорошо", easy: "Легко", noDue: "На сегодня повторений нет 🎉",
      newCard: "Новая карточка", front: "Лицевая сторона", backSide: "Обратная сторона", deck: "Колода",
      correct: "Верно!", wrong: "Неверно", explanation: "Пояснение", next: "Далее", score: "Результат: {c}/{n}", done: "Викторина дня завершена",
      license: "Лицензия", sentences: "{n} предл.",
    },
    admin: {
      title: "Управление", staff: "Сотрудники", kpi: "KPI", audit: "Журнал аудита", role: "Роль", active: "Активен",
      casesDone: "Завершённые случаи", saved: "Спасённые маркеры", panels: "Утверждённые панели",
      verify: "Проверить цепочку", chainOk: "Цепочка аудита цела ({n} записей)", chainBroken: "Внимание! Цепочка нарушена на #{id}",
      specialty: "Специальность",
    },
    audit: {
      "biopsy.create": "Зарегистрирована биопсия {code}", "biopsy.approve": "Утверждена панель {code}: −{tests} тест.",
      "biopsy.update": "Изменена биопсия {code}", "biopsy.scoring": "Сохранён скоринг {code}", "biopsy.report": "Завершена {code}",
      "consilium.open": "Открыт консилиум {code}", "consilium.close": "Закрыт консилиум {code}", "consilium.comment": "Мнение в консилиуме {code}",
      "marker.create": "Добавлен маркер: {name}", "marker.custom_create": "Добавлен свой маркер: {name}", "marker.update": "Изменён маркер: {name}",
      "marker.passport_verify": "Паспорт подтверждён: {name}", "stock.receive": "Принят лот: {name} {lot} (+{quantity})",
      "stock.adjust": "Корректировка: {name} ({delta})", "stock.write_off": "Списание: {name} ({delta})",
      "image.upload": "Загружено изображение #{id}", "image.pins": "Метки изображения #{id}", "user.register": "Новый пользователь",
      "user.update": "Изменён пользователь: {user}", "user.web_login": "Вход через браузер", "atlas.update": "Изменён атлас: {slug}",
      "book.import": "Импортирована книга: {title}",
    },
    img: { kind: "Тип", micro: "Микроскопия", macro: "Макроскопия", stain: "Окраска", captionUz: "Подпись (UZ)", captionRu: "Подпись (RU)", file: "Файл", pins: "Метки", addPin: "Нажмите на изображение, чтобы поставить метку", pinLabel: "Название метки" },
  },
};

function merge(target, extra) {
  for (const [k, v] of Object.entries(extra)) {
    if (v && typeof v === "object" && !Array.isArray(v) && typeof target[k] === "object") merge(target[k], v);
    else target[k] = v;
  }
}
merge(DICT, STRINGS);

const I18nContext = createContext(null);

function lookup(lang, key) {
  // Keys may themselves contain dots (e.g. audit action codes "biopsy.approve"),
  // so at each level try the whole remaining key before descending.
  const parts = key.split(".");
  let node = DICT[lang];
  for (let i = 0; i < parts.length && node != null; i++) {
    const rest = parts.slice(i).join(".");
    if (typeof node === "object" && rest in node) return node[rest];
    node = node[parts[i]];
  }
  return undefined;
}

function readStoredLang() {
  try {
    const v = localStorage.getItem("pathouz.lang");
    if (v === "uz" || v === "ru") return v;
  } catch {}
  return null;
}

export function I18nProvider({ children }) {
  const [lang, setLangState] = useState(() => readStoredLang() || "uz");

  const setLang = useCallback((next) => {
    setLangState(next);
    try { localStorage.setItem("pathouz.lang", next); } catch {}
    document.documentElement.lang = next;
  }, []);

  const t = useCallback((key, vars) => {
    let s = lookup(lang, key) ?? lookup("uz", key) ?? key;
    if (typeof s === "string" && vars) s = s.replace(/\{(\w+)\}/g, (_, k) => (vars[k] ?? ""));
    return s;
  }, [lang]);

  /** Pick the current language from a {uz, ru} content object, falling back to the other one. */
  const L = useCallback((obj) => {
    if (obj == null) return "";
    if (typeof obj === "string") return obj;
    return obj[lang] || obj.uz || obj.ru || "";
  }, [lang]);

  const value = useMemo(() => ({ lang, setLang, t, L, hasStored: readStoredLang() != null }), [lang, setLang, t, L]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  return useContext(I18nContext);
}
