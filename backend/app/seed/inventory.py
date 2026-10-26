"""Starter IGX inventory.

Lab passports below are typical example protocols for orientation only — every laboratory
must validate retrieval, dilution and incubation on its own platform before clinical use.
Tandem pairings encode accepted diagnostic indications; inventory status only re-ranks them.
"""
from datetime import date, datetime, timedelta, timezone

EDTA = "EDTA pH 9.0"
CITRATE = "Citrate pH 6.0"

# name, clone, organ, localization, (buffer, retrieval_min, dilution, incubation_min, control), description uz/ru
MARKERS = [
    ("ER", "SP1", "breast", "nuclear", (EDTA, 30, "RTU", 32, "Normal breast / Cervix"),
     ("Estrogen retseptori — gormonoterapiya tanlovi uchun majburiy.", "Рецептор эстрогена — обязателен для выбора гормонотерапии.")),
    ("PR", "1E2", "breast", "nuclear", (EDTA, 30, "RTU", 32, "Normal breast / Endometrium"),
     ("Progesteron retseptori; ER bilan birga baholanadi.", "Рецептор прогестерона; оценивается вместе с ER.")),
    ("HER2", "4B5", "breast", "membranous", (EDTA, 30, "RTU", 16, "Breast carcinoma HER2 0/1+/2+/3+ control slide"),
     ("ERBB2 oqsili; ASCO/CAP 0–3+ shkalasida baholanadi.", "Белок ERBB2; оценивается по шкале ASCO/CAP 0–3+.")),
    ("Ki-67", "MIB-1", "breast", "nuclear", (EDTA, 20, "1:100", 30, "Tonsil"),
     ("Proliferatsiya indeksi (%).", "Индекс пролиферации (%).")),
    ("CK5/6", "D5/16B4", "breast", "cytoplasmic", (EDTA, 20, "1:50", 30, "Tonsil (squamous epithelium)"),
     ("Bazal/yassi epiteliy keratini.", "Кератин базального/плоского эпителия.")),
    ("GATA3", "L50-823", "breast", "nuclear", (EDTA, 20, "1:200", 30, "Normal breast / Urothelium"),
     ("Ko'krak bezi va urotelial kelib chiqish markeri.", "Маркер происхождения из молочной железы и уротелия.")),
    ("E-cadherin", "36", "breast", "membranous", (EDTA, 20, "1:100", 30, "Normal breast"),
     ("Duktal va lobulyar karsinomani farqlaydi.", "Различает протоковую и дольковую карциному.")),
    ("p63", "4A4", "breast", "nuclear", (EDTA, 20, "1:100", 30, "Tonsil / Normal prostate"),
     ("Mioepitelial va bazal hujayralar.", "Миоэпителиальные и базальные клетки.")),
    ("CK7", "OV-TL 12/30", "lung", "cytoplasmic", (EDTA, 20, "1:200", 30, "Normal lung"),
     ("CK7/CK20 profili — kelib chiqish joyini aniqlash.", "Профиль CK7/CK20 — определение первичного очага.")),
    ("CK20", "Ks20.8", "colon", "cytoplasmic", (EDTA, 20, "1:100", 30, "Normal colon"),
     ("Oshqozon-ichak va urotelial keratin.", "Кератин ЖКТ и уротелия.")),
    ("TTF-1", "8G7G3/1", "lung", "nuclear", (EDTA, 20, "1:100", 30, "Normal lung / Thyroid"),
     ("O'pka va qalqonsimon bez kelib chiqishi.", "Происхождение из лёгкого и щитовидной железы.")),
    ("Napsin A", "IP64", "lung", "cytoplasmic", (EDTA, 20, "1:200", 30, "Normal lung"),
     ("O'pka adenokarsinomasi uchun qo'shimcha marker.", "Дополнительный маркер аденокарциномы лёгкого.")),
    ("p40", "BC28", "lung", "nuclear", (EDTA, 20, "1:100", 30, "Tonsil"),
     ("Yassi hujayrali differensiatsiyaning eng o'ziga xos markeri.", "Наиболее специфичный маркер плоскоклеточной дифференцировки.")),
    ("CDX2", "EPR2764Y", "colon", "nuclear", (EDTA, 20, "1:200", 30, "Normal colon"),
     ("Ichak differensiatsiyasi.", "Кишечная дифференцировка.")),
    ("SATB2", "EP281", "colon", "nuclear", (EDTA, 20, "1:100", 30, "Normal colon / Appendix"),
     ("Kolorektal kelib chiqish markeri.", "Маркер колоректального происхождения.")),
    ("MLH1", "ES05", "colon", "nuclear", (EDTA, 40, "1:50", 30, "Normal colon / Tonsil (internal control)"),
     ("MMR oqsili; yo'qolishi MSI ni ko'rsatadi.", "Белок MMR; утрата указывает на MSI.")),
    ("PMS2", "EP51", "colon", "nuclear", (EDTA, 40, "1:50", 30, "Normal colon / Tonsil"),
     ("MMR oqsili (MLH1 juftligi).", "Белок MMR (пара MLH1).")),
    ("MSH2", "G219-1129", "colon", "nuclear", (EDTA, 30, "1:200", 30, "Normal colon / Tonsil"),
     ("MMR oqsili.", "Белок MMR.")),
    ("MSH6", "EP49", "colon", "nuclear", (EDTA, 30, "1:100", 30, "Normal colon / Tonsil"),
     ("MMR oqsili (MSH2 juftligi).", "Белок MMR (пара MSH2).")),
    ("Synaptophysin", "MRQ-40", "lung", "cytoplasmic", (EDTA, 20, "1:100", 30, "Appendix / Pancreas (islets)"),
     ("Neyroendokrin differensiatsiya.", "Нейроэндокринная дифференцировка.")),
    ("Chromogranin A", "LK2H10", "lung", "cytoplasmic", (CITRATE, 20, "1:200", 30, "Appendix / Pancreas (islets)"),
     ("Neyrosekretor granulalar.", "Нейросекреторные гранулы.")),
    ("INSM1", "A-8", "lung", "nuclear", (EDTA, 30, "1:100", 30, "Pancreas (islets)"),
     ("Neyroendokrin differensiatsiyaning yadro markeri.", "Ядерный маркер нейроэндокринной дифференцировки.")),
    ("CD117", "YR145", "stomach", "membranous/cytoplasmic", (EDTA, 20, "1:200", 30, "GIST / Mast cells"),
     ("KIT — GIST markeri.", "KIT — маркер GIST.")),
    ("DOG1", "SP31", "stomach", "membranous/cytoplasmic", (EDTA, 20, "1:100", 30, "GIST / Appendix (ICC)"),
     ("KIT-manfiy GIST uchun ham sezgir.", "Чувствителен и при KIT-негативных GIST.")),
    ("SOX10", "EP268", "skin", "nuclear", (EDTA, 20, "1:100", 30, "Melanoma / Peripheral nerve"),
     ("Melanotsitar va shvann hujayralari.", "Меланоцитарные и шванновские клетки.")),
    ("S100", "polyclonal", "skin", "nuclear/cytoplasmic", (EDTA, 20, "1:1000", 30, "Peripheral nerve / Skin"),
     ("Sezgir, ammo o'ziga xosligi past.", "Чувствителен, но малоспецифичен.")),
    ("Melan-A", "A103", "skin", "cytoplasmic", (EDTA, 20, "1:50", 30, "Melanoma / Skin (melanocytes)"),
     ("Melanotsitar differensiatsiya.", "Меланоцитарная дифференцировка.")),
    ("CD20", "L26", "lymph", "membranous", (EDTA, 20, "1:200", 30, "Tonsil"),
     ("B-limfotsitlar.", "B-лимфоциты.")),
    ("CD3", "2GV6", "lymph", "membranous/cytoplasmic", (EDTA, 20, "RTU", 30, "Tonsil"),
     ("T-limfotsitlar.", "T-лимфоциты.")),
    ("CD30", "Ber-H2", "lymph", "membranous/Golgi", (EDTA, 30, "1:50", 30, "Hodgkin lymphoma / Tonsil (activated cells)"),
     ("Xodjkin va anaplastik limfoma.", "Лимфома Ходжкина и анапластическая лимфома.")),
    ("PAX8", "MRQ-50", "kidney", "nuclear", (EDTA, 20, "1:100", 30, "Normal kidney / Thyroid"),
     ("Buyrak, Myuller va qalqonsimon bez kelib chiqishi.", "Почечное, мюллерово и тиреоидное происхождение.")),
    ("NKX3.1", "EP356", "prostate", "nuclear", (EDTA, 20, "1:100", 30, "Normal prostate"),
     ("Prostata kelib chiqishining o'ziga xos markeri.", "Специфичный маркер простатического происхождения.")),
]

# marker -> (routine triggers, reason uz, reason ru)
TANDEM = {
    "GATA3": (["ER", "PR", "HER2", "Ki-67", "CK7"],
              "Metastaz yoki uch karra manfiy o'smada ko'krak bezi kelib chiqishini tasdiqlaydi.",
              "Подтверждает происхождение из молочной железы при метастазе или тройном негативном раке."),
    "E-cadherin": (["ER", "PR", "HER2", "Ki-67"],
                   "Morfologiya noaniq bo'lsa duktal (+) va lobulyar (−) karsinomani farqlaydi — davolash va kuzatuvga ta'sir qiladi.",
                   "При неясной морфологии различает протоковую (+) и дольковую (−) карциному — влияет на лечение и наблюдение."),
    "p63": (["ER", "PR", "CK5/6"],
            "Mioepitelial qavat bor-yo'qligi — in situ va invaziv o'smani farqlash.",
            "Наличие миоэпителиального слоя — различие in situ и инвазивного роста."),
    "CK5/6": (["ER", "PR", "HER2"],
              "Uch karra manfiy o'smada bazal-simon fenotipni aniqlaydi.",
              "Выявляет базальноподобный фенотип при тройном негативном раке."),
    "p40": (["CK5/6", "TTF-1", "Napsin A"],
            "Past differensiallashgan NSCLC da yassi hujayrali karsinomani tasdiqlaydi yoki inkor qiladi.",
            "Подтверждает или исключает плоскоклеточный рак при низкодифференцированном НМРЛ."),
    "TTF-1": (["p40", "CK5/6", "CK7"],
              "Adenokarsinoma va yassi hujayrali karsinomani farqlash; o'pka kelib chiqishi.",
              "Разграничение аденокарциномы и плоскоклеточного рака; лёгочное происхождение."),
    "Napsin A": (["TTF-1"],
                 "TTF-1 bilan birga o'pka adenokarsinomasi uchun o'ziga xoslikni oshiradi.",
                 "Вместе с TTF-1 повышает специфичность для аденокарциномы лёгкого."),
    "SATB2": (["CK20", "CDX2", "CK7"],
              "CDX2 bilan birga kolorektal kelib chiqishni tasdiqlaydi (noma'lum birlamchi o'chog'li metastazda).",
              "Вместе с CDX2 подтверждает колоректальное происхождение (метастаз без первичного очага)."),
    "CDX2": (["CK20", "CK7"],
             "Ichak differensiatsiyasini ko'rsatadi.", "Указывает на кишечную дифференцировку."),
    "MLH1": (["CDX2", "CK20", "SATB2"],
             "Kolorektal saratonda universal MMR skriningi (Linch sindromi, immunoterapiya).",
             "Универсальный скрининг MMR при колоректальном раке (синдром Линча, иммунотерапия)."),
    "PMS2": (["MLH1", "CDX2"], "MMR paneli: MLH1 bilan juft.", "Панель MMR: пара к MLH1."),
    "MSH2": (["MLH1", "CDX2"], "MMR paneli to'liqligi.", "Полнота панели MMR."),
    "MSH6": (["MSH2", "CDX2"], "MMR paneli: MSH2 bilan juft.", "Панель MMR: пара к MSH2."),
    "INSM1": (["Synaptophysin", "Chromogranin A"],
              "Yadro neyroendokrin markeri — xromogranin kuchsiz bo'lganda (mayda hujayrali karsinoma) sezgir.",
              "Ядерный нейроэндокринный маркер — чувствителен при слабом хромогранине (мелкоклеточный рак)."),
    "Chromogranin A": (["Synaptophysin"], "Neyroendokrin panelni to'ldiradi.", "Дополняет нейроэндокринную панель."),
    "DOG1": (["CD117"], "KIT-manfiy GIST holatlarini aniqlaydi.", "Выявляет KIT-негативные GIST."),
    "SOX10": (["S100", "Melan-A"],
              "Desmoplastik melanomada ham musbat; S100 dan o'ziga xosroq.",
              "Позитивен и при десмопластической меланоме; специфичнее S100."),
    "Melan-A": (["S100"], "Melanotsitar differensiatsiyani tasdiqlaydi.", "Подтверждает меланоцитарную дифференцировку."),
    "CD3": (["CD20"], "B- va T-hujayrali populyatsiyalarni farqlash.", "Разграничение B- и T-клеточных популяций."),
    "CD30": (["CD20", "CD3"], "Xodjkin limfomasi yoki ALCL ga shubhada.", "При подозрении на лимфому Ходжкина или ALCL."),
    "PAX8": (["CK7"], "Buyrak, Myuller yoki qalqonsimon bez kelib chiqishi.", "Почечное, мюллерово или тиреоидное происхождение."),
}

# marker -> (lots [(lot, days_to_expiry, qty)], tests used in the last 30 days)
STOCK = {
    "ER": ([("ER-24A", 210, 160)], 46), "PR": ([("PR-24A", 190, 150)], 44),
    "HER2": ([("HER2-24B", 160, 120)], 41), "Ki-67": ([("KI-24C", 240, 180)], 47),
    "CK5/6": ([("CK56-24A", 150, 70)], 22),
    "GATA3": ([("GATA3-23F", 34, 38)], 2), "E-cadherin": ([("ECAD-23E", 48, 30)], 1),
    "SATB2": ([("SATB2-23D", 41, 25)], 0), "MLH1": ([("MLH1-23K", 55, 20)], 3),
    "p40": ([("P40-23H", 38, 27)], 2), "p63": ([("P63-24A", 300, 40)], 8),
    "CK7": ([("CK7-24B", 280, 90)], 24), "CK20": ([("CK20-24B", 260, 80)], 19),
    "TTF-1": ([("TTF1-24A", 200, 60)], 15), "Napsin A": ([("NAPA-24A", 120, 30)], 6),
    "CDX2": ([("CDX2-24C", 230, 50)], 12),
    "PMS2": ([("PMS2-24A", 170, 22)], 3), "MSH2": ([("MSH2-24A", 175, 22)], 3), "MSH6": ([("MSH6-24A", 175, 22)], 3),
    "Synaptophysin": ([("SYP-24A", 220, 45)], 9), "Chromogranin A": ([("CGA-24A", 25, 15)], 4),
    "INSM1": ([("INSM1-24A", 320, 20)], 1), "CD117": ([("CD117-24A", 180, 25)], 4),
    "DOG1": ([("DOG1-24A", 90, 18)], 2), "SOX10": ([("SOX10-24A", 270, 30)], 5),
    "S100": ([("S100-24A", 300, 60)], 11), "Melan-A": ([("MELA-24A", 52, 12)], 2),
    "CD20": ([("CD20-24A", 250, 70)], 14), "CD3": ([("CD3-24A", 250, 70)], 14),
    "CD30": ([("CD30-23X", -10, 5), ("CD30-24A", 200, 20)], 3),
    "PAX8": ([("PAX8-24A", 210, 30)], 6), "NKX3.1": ([("NKX-24A", 230, 8)], 4),
}


# Antibodies on the laboratory's own shelf (from the rack photo), not yet in MARKERS above.
# Added without lots or a lab passport: the lab enters lot, expiry, quantity and its own
# validated protocol in the IGX Ombor screen.
# name, organ, localization, description uz/ru
LAB_MARKERS = [
    ("p16", "cervix", "nuclear/cytoplasmic", ("HPV bilan bog'liq displaziya va karsinoma surrogat markeri.", "Суррогатный маркер ВПЧ-ассоциированной дисплазии и карциномы.")),
    ("CD138", "lymph", "membranous", ("Plazmotsitlar va plazmotsitar o'smalar.", "Плазматические клетки и плазмоклеточные опухоли.")),
    ("EMA", "other", "membranous", ("Epitelial membrana antigeni.", "Эпителиальный мембранный антиген.")),
    ("NSE", "other", "cytoplasmic", ("Neyronga xos enolaza; neyroendokrin differensiatsiya.", "Нейрон-специфическая енолаза; нейроэндокринная дифференцировка.")),
    ("SALL4", "other", "nuclear", ("Germinogen hujayrali o'smalar markeri.", "Маркер герминогенных опухолей.")),
    ("CD56", "other", "membranous", ("NCAM; neyroendokrin va NK-hujayralar.", "NCAM; нейроэндокринные и NK-клетки.")),
    ("CD1a", "lymph", "membranous", ("Langerhans hujayralari va kortikal timotsitlar.", "Клетки Лангерганса и кортикальные тимоциты.")),
    ("STAT6", "other", "nuclear", ("Solitar fibroz o'sma (NAB2-STAT6).", "Солитарная фиброзная опухоль (NAB2-STAT6).")),
    ("MyoD1", "other", "nuclear", ("Skelet mushagi differensiatsiyasi (rabdomiosarkoma).", "Скелетно-мышечная дифференцировка (рабдомиосаркома).")),
    ("CD15", "lymph", "membranous/Golgi", ("Reed-Sternberg hujayralari, granulotsitlar.", "Клетки Рида-Штернберга, гранулоциты.")),
    ("OCT3/4", "other", "nuclear", ("Seminoma va embrional karsinoma.", "Семинома и эмбриональная карцинома.")),
    ("CD34", "other", "membranous", ("Endoteliy, gemopoetik o'tmishdoshlar, ayrim mezenximal o'smalar.", "Эндотелий, гемопоэтические предшественники, ряд мезенхимальных опухолей.")),
    ("TdT", "lymph", "nuclear", ("Limfoblastlar (limfoblast limfoma/leykoz).", "Лимфобласты (лимфобластная лимфома/лейкоз).")),
    ("CD10", "other", "membranous", ("Germinal markaz B-hujayralari, endometrial stroma, buyrak.", "B-клетки герминативного центра, эндометриальная строма, почка.")),
    ("NeuN", "other", "nuclear", ("Neyronlar yadrosi.", "Ядра нейронов.")),
    ("S100P", "other", "nuclear/cytoplasmic", ("Pankreatobiliar va urotelial karsinomalar.", "Панкреатобилиарные и уротелиальные карциномы.")),
    ("CD45 (LCA)", "lymph", "membranous", ("Umumiy leykotsitar antigen.", "Общий лейкоцитарный антиген.")),
    ("HMB45", "skin", "cytoplasmic", ("Melanotsitar differensiatsiya, PEComa.", "Меланоцитарная дифференцировка, PEComa.")),
    ("PTEN", "other", "nuclear/cytoplasmic", ("O'sma supressori; yo'qolishi baholanadi.", "Опухолевый супрессор; оценивается утрата.")),
    ("CD68", "lymph", "cytoplasmic", ("Makrofaglar va gistiotsitlar.", "Макрофаги и гистиоциты.")),
    ("INI1", "other", "nuclear", ("SMARCB1; yo'qolishi rabdoid o'smalarda.", "SMARCB1; утрата при рабдоидных опухолях.")),
    ("Calretinin", "other", "nuclear/cytoplasmic", ("Mezotelial differensiatsiya.", "Мезотелиальная дифференцировка.")),
    ("CD99", "other", "membranous", ("Ewing sarkomasi va boshqa mayda dumaloq hujayrali o'smalar.", "Саркома Юинга и другие мелкокруглоклеточные опухоли.")),
    ("SOX11", "lymph", "nuclear", ("Mantiya hujayrali limfoma.", "Лимфома из клеток мантии.")),
    ("p53", "other", "nuclear", ("TP53 mutatsiyasi surrogati (yovvoyi / aberrant tip).", "Суррогат мутации TP53 (дикий / аберрантный тип).")),
    ("PSA", "prostate", "cytoplasmic", ("Prostata kelib chiqishi.", "Простатическое происхождение.")),
    ("BRAF V600E", "other", "cytoplasmic", ("BRAF V600E mutant oqsili.", "Мутантный белок BRAF V600E.")),
    ("Vimentin", "other", "cytoplasmic", ("Mezenximal oraliq filament.", "Мезенхимальный промежуточный филамент.")),
    ("CD5", "lymph", "membranous", ("T-hujayralar; KLL/MKL va mantiya limfomasi.", "T-клетки; ХЛЛ/МЛЛ и лимфома из клеток мантии.")),
    ("YAP1", "other", "nuclear", ("Medulloblastoma molekulyar guruhlari (GAB1 bilan).", "Молекулярные группы медуллобластомы (вместе с GAB1).")),
    ("GAB1", "other", "cytoplasmic", ("SHH-medulloblastoma (YAP1 bilan).", "SHH-медуллобластома (вместе с YAP1).")),
    ("ALK", "lung", "cytoplasmic", ("ALK qayta joylashuvi: o'pka adenokarsinomasi, ALCL, IMT.", "Перестройка ALK: аденокарцинома лёгкого, ALCL, ВМО.")),
    ("GFAP", "other", "cytoplasmic", ("Glial differensiatsiya.", "Глиальная дифференцировка.")),
    ("CD79a", "lymph", "membranous/cytoplasmic", ("B-hujayra va plazmotsitlar.", "B-клетки и плазматические клетки.")),
    ("SMA", "other", "cytoplasmic", ("Silliq mushak aktini.", "Гладкомышечный актин.")),
    ("WT1", "other", "nuclear", ("Mezoteliy, seroz karsinoma, Wilms o'smasi.", "Мезотелий, серозная карцинома, опухоль Вильмса.")),
    ("PanCK", "other", "cytoplasmic", ("Keng spektrli sitokeratin (AE1/AE3); epitelial kelib chiqish.", "Панцитокератин (AE1/AE3); эпителиальное происхождение.")),
    ("Cyclin D1", "lymph", "nuclear", ("Mantiya hujayrali limfoma, ayrim karsinomalar.", "Лимфома из клеток мантии, ряд карцином.")),
    ("Olig2", "other", "nuclear", ("Glial o'smalar (oligodendroglioma, astrotsitoma).", "Глиальные опухоли (олигодендроглиома, астроцитома).")),
    ("CD31", "other", "membranous", ("Endotelial marker; tomir o'smalari.", "Эндотелиальный маркер; сосудистые опухоли.")),
    ("PLAP", "other", "membranous/cytoplasmic", ("Germinogen hujayrali o'smalar.", "Герминогенные опухоли.")),
    ("Bcl-2", "lymph", "cytoplasmic", ("Follikulyar limfomani reaktiv follikuldan farqlash.", "Отличие фолликулярной лимфомы от реактивного фолликула.")),
    ("ATRX", "other", "nuclear", ("Diffuz gliomalarda yo'qolishi baholanadi.", "Оценка утраты при диффузных глиомах.")),
    ("Desmin", "other", "cytoplasmic", ("Mushak differensiatsiyasi.", "Мышечная дифференцировка.")),
    ("Bcl-6", "lymph", "nuclear", ("Germinal markaz B-hujayralari.", "B-клетки герминативного центра.")),
    ("AMACR (P504S)", "prostate", "cytoplasmic", ("Prostata adenokarsinomasi (p63 bilan).", "Аденокарцинома простаты (вместе с p63).")),
    ("IDH1 R132H", "other", "cytoplasmic", ("IDH1 R132H mutant oqsili (gliomalar).", "Мутантный белок IDH1 R132H (глиомы).")),
    ("PD-L1", "lung", "membranous", ("Immunoterapiyaga tanlov (TPS/CPS).", "Отбор на иммунотерапию (TPS/CPS).")),
    ("H3K27me3", "other", "nuclear", ("Yo'qolishi: MPNST, diffuz o'rta chiziq gliomasi.", "Утрата: MPNST, диффузная глиома средней линии.")),
]


def build(today: date | None = None):
    """Return (markers, lots_by_marker, usage_by_marker) ready to insert."""
    today = today or date.today()
    markers = []
    for name, clone, organ, loc, (buf, rt, dil, inc, ctrl), (d_uz, d_ru) in MARKERS:
        triggers, r_uz, r_ru = TANDEM.get(name, ([], "", ""))
        markers.append(dict(
            name=name, clone=clone, organ=organ, localization=loc,
            description={"uz": d_uz, "ru": d_ru}, tandem_with=triggers, reason={"uz": r_uz, "ru": r_ru},
            lab_passport={"retrieval_buffer": buf, "retrieval_time_min": rt, "dilution": dil,
                          "incubation_min": inc, "control_tissue": ctrl,
                          "notes": "Example protocol — validate locally before clinical use."},
        ))
    for name, organ, loc, (d_uz, d_ru) in LAB_MARKERS:
        markers.append(dict(name=name, organ=organ, localization=loc, description={"uz": d_uz, "ru": d_ru},
                            tandem_with=[], reason={"uz": "", "ru": ""}, lab_passport={}))
    lots = {n: [(lot, today + timedelta(days=d), q) for lot, d, q in spec[0]] for n, spec in STOCK.items()}
    now = datetime.now(timezone.utc)
    # Spread each marker's past tests evenly over the window (offset by half a step so none land "now").
    usage = {n: [now - timedelta(days=(i + 0.5) * 30 / spec[1]) for i in range(spec[1])] for n, spec in STOCK.items()}
    return markers, lots, usage
