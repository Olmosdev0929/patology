"""Localized macro/micro description templates. Placeholders in [brackets] are filled by the pathologist."""

TEMPLATES = [
    {
        "id": "breast-core", "organ": "breast", "kind": "macro",
        "title": {"uz": "Ko'krak bezi kor-biopsiyasi", "ru": "Кор-биопсия молочной железы"},
        "text": {
            "uz": "Formalinda [N] ta ustunsimon to'qima bo'lagi, uzunligi [x–y] mm, diametri [d] mm, oq-kulrang rangli. To'liq [K] ta kassetaga joylandi.",
            "ru": "В формалине [N] столбиков ткани длиной [x–y] мм, диаметром [d] мм, бело-серого цвета. Полностью уложены в [K] кассет(ы).",
        },
    },
    {
        "id": "breast-idc-micro", "organ": "breast", "kind": "micro",
        "title": {"uz": "Invaziv karsinoma NST — mikroskopiya", "ru": "Инвазивная карцинома NST — микроскопия"},
        "text": {
            "uz": "Desmoplastik stromada uyalar va tortmalar shaklida invaziv karsinoma. Naychalar: [1–3], yadro pleomorfizmi: [1–3], mitozlar: [1–3] → Nottingem darajasi [G1–G3]. Limfovaskulyar invaziya: [bor/yo'q]. DCIS komponenti: [bor/yo'q].",
            "ru": "Инвазивная карцинома в виде гнёзд и тяжей в десмопластической строме. Тубулы: [1–3], ядерный плеоморфизм: [1–3], митозы: [1–3] → степень по Ноттингему [G1–G3]. Лимфоваскулярная инвазия: [есть/нет]. Компонент DCIS: [есть/нет].",
        },
    },
    {
        "id": "colon-resection", "organ": "colon", "kind": "macro",
        "title": {"uz": "Yo'g'on ichak rezeksiyasi", "ru": "Резекция толстой кишки"},
        "text": {
            "uz": "Yo'g'on ichak segmenti, uzunligi [L] sm. Proksimal chetidan [a] sm, distal chetidan [b] sm masofada [o'lcham] sm li [ekzofit/yarali/halqasimon] o'sma. Ichak devoriga invaziya chuqurligi: [..]. Radial chet: [..] mm. Limfa tugunlari: [N] ta topildi.",
            "ru": "Сегмент толстой кишки длиной [L] см. На расстоянии [a] см от проксимального и [b] см от дистального края — [экзофитная/изъязвлённая/циркулярная] опухоль [размер] см. Глубина инвазии стенки: [..]. Радиальный край: [..] мм. Найдено лимфоузлов: [N].",
        },
    },
    {
        "id": "lung-biopsy-micro", "organ": "lung", "kind": "micro",
        "title": {"uz": "O'pka biopsiyasi — NSCLC", "ru": "Биопсия лёгкого — НМРЛ"},
        "text": {
            "uz": "Bronx/o'pka to'qimasida [atsinar/solid/papillyar] tuzilmali nomayda hujayrali karsinoma. Keratinlanish: [bor/yo'q]. IHC: TTF-1 [..], p40 [..]. Molekulyar test uchun material yetarliligi: [yetarli/yetarli emas].",
            "ru": "В ткани бронха/лёгкого немелкоклеточная карцинома [ацинарного/солидного/папиллярного] строения. Ороговение: [есть/нет]. ИГХ: TTF-1 [..], p40 [..]. Достаточность материала для молекулярного теста: [достаточно/недостаточно].",
        },
    },
    {
        "id": "generic-micro", "organ": None, "kind": "micro",
        "title": {"uz": "Umumiy mikroskopik shablon", "ru": "Общий микроскопический шаблон"},
        "text": {
            "uz": "Taqdim etilgan material: [..]. Arxitektura: [..]. Hujayra xususiyatlari: [..]. Stroma: [..]. Nekroz: [..]. Mitozlar: [..] / 10 KKM. Chetlar: [..].",
            "ru": "Представленный материал: [..]. Архитектура: [..]. Клеточные характеристики: [..]. Строма: [..]. Некроз: [..]. Митозы: [..] / 10 ПЗБУ. Края: [..].",
        },
    },
]
