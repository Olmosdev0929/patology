# PathoUz v6.0 — LIS, IGX inventar va Smart Academy

Patomorfologiya laboratoriyasi uchun platforma. Veb-ilova va Telegram Mini App sifatida ishlaydi, interfeys o'zbek va rus tillarida (`O'Z` / `РУ`), yorug' va tungi mavzu bilan.

Pastki navigatsiya: **Biopsiyalar · IGX Ombor · Atlas Baza · Ta'lim · Galereya**. Sarlavhada umumiy qidiruv (kasallik, ICD kodi, marker, biopsiya), bot buyruqlari, til va mavzu almashtirgich.

| Modul | Imkoniyatlar |
|---|---|
| **1. Atlas va Galereya** | 11 a'zo/tizim, 17 kasallik (UZ/RU): klinika, makro, mikro, IHC, differensial diagnoz, prognoz. Patolog yangi kasallik qo'shadi. Galereya (makro / mikro / IHC): lightbox, zoom, raqamlangan belgilar. 8 ta boshlang'ich rasm — **sxematik chizmalar**, haqiqiy preparat fotosuratlari emas |
| **2. Biopsiya qabuli + Smart Tandem** | Holatni ro'yxatga olish (`B-2026-001`), a'zoga qarab asosiy markerlar, klinik jihatdan juftlangan markerlarni tavsiya qilish (muddati yaqin va sekin sarflanadiganlar oldinda), inventardan qidirish yoki yangi marker nomini yozish |
| **3. Skoring va konsilium** | Allred (ER/PR), HER2 ASCO/CAP (shu jumladan HER2-low/ultralow), Ki-67, St Gallen surrogat turlari. Konsilium: fikrlar va rasmlar biriktirish |
| **4. IGX Ombor** | Uch bo'lim: qoldiq, Aqlli Tandem, sarf statistikasi (kunlik grafik, eng ko'p sarflanganlar, zaxira yetadigan kunlar). Lotlar bo'yicha FEFO, 🔴 muddati yaqin (<60 kun) / 🟣 sekin / 🟢 tez sarflanadigan toifalar, laboratoriya pasporti (bufer, suyultirish, nazorat to'qimasi, joylashuv) va uni tasdiqlash. Panel tasdiqlanganda har bir markerdan avtomatik −1 test yechiladi |
| **5. Ta'lim (Smart Academy)** | Kitoblar, slaydlar, videolar (YouTube havolasi ilova ichida ochiladi); gapma-gap parallel o'quvchi (EN + UZ + RU, Web Speech orqali ovoz, atamalar), bir bosishda Anki kartasi, SM-2 takrorlash (Again/Hard/Good/Easy), kunlik holatli viktorina |
| **6. Admin va xavfsizlik** | RBAC (4 rol), xodimlar KPI, hash-zanjirli audit jurnali (PostgreSQL'da `UPDATE`/`DELETE` trigger bilan bloklangan) |

## Telegram bot menyusi

Asosiy ishlarni ilovani ochmasdan, bot ichida tugmalar orqali bajarish mumkin. `/start` bot va ilova haqida ma'lumot, foydalanish yo'riqnomasi va asosiy menyuni yuboradi; `/menu` menyuni qayta ochadi, `/cancel` boshlangan amalni bekor qiladi.

| Bo'lim | Kim uchun | Imkoniyatlar |
|---|---|---|
| 🧫 Biopsiyalar | patolog, laborant | yangi holat (a'zo → bemor → yosh → jins → klinik taxmin → panel, Smart Tandem takliflari), ro'yxat, holat kartasi, panelni tasdiqlash (patolog), hisobot va stiker havolasi |
| 🧪 IGX Ombor | patolog, laborant | qoldiq, muddati yaqin / kam / tugagan markerlar, qidirish, lot qabul qilish va hisobdan chiqarish (laborant) |
| 📊 Sarf statistikasi | patolog, laborant | 30 kunlik sarf, eng ko'p ishlatilganlar, necha kunga yetishi |
| 📚 Atlas | hamma | kasallik, ICD-10 yoki marker bo'yicha qidirish |
| 🎓 Ta'lim | hamma | kunlik viktorina, Anki takrorlash |
| 👑 Admin | Super Admin | xodimlarga rol berish, bloklash |

Rollar API bilan bir xil tekshiriladi; laborantga bemor ismi bosh harflar bilan ko'rsatiladi. Bot orqali qilingan o'zgarishlar audit jurnaliga `"via": "bot"` belgisi bilan yoziladi.

## Katta kitoblar (yuzlab MB'lik PDF)

Admin **Ta'lim → Kitoblar → PDF kitob yuklash** orqali 2 GB gacha (`MAX_BOOK_MB`) PDF joylaydi.

| Bosqich | Qanday ishlaydi |
|---|---|
| Yuklash | 8 MB'lik bo'laklar, har biri SHA-256 bilan tekshiriladi. Aloqa uzilsa avtomatik qayta urinadi; "To'xtatish" va "Davom ettirish" tugmalari bor. Ilova yopilsa, o'sha faylni qayta tanlang, yuklash qolgan joyidan davom etadi. Server faylni to'g'ridan-to'g'ri diskka yozadi, xotiraga to'liq olmaydi |
| Tekshiruv | Disk joyi oldindan tekshiriladi (`DISK_RESERVE_MB`), PDF imzosi va SHA-256 dublikati aniqlanadi |
| Veb uchun optimallashtirish | Fayl oxiriga standart *incremental update* qo'shiladi (asl baytlar o'zgarmaydi). Shundan so'ng pdf.js kitobni butun faylni emas, faqat oxirini o'qib ochadi. 391 MB'lik, 2000 sahifali sinov kitobi: **392 so'rov / 391 MB → 5 so'rov / 3,1 MB**, ochilish vaqti 11,5 s → 1,9 s |
| Matn indeksi | Fonda, alohida jarayonda, 200 sahifalik oynalar bilan ishlaydi; xotira chegarasi `PDF_WORKER_MEM_MB`. Sinovda 2000 sahifa 8 soniyada indekslandi, ishchi jarayon xotirasi 75 MB, server xotirasi 224 MB dan oshmadi |
| O'qish | pdf.js HTTP Range orqali faqat ko'rilayotgan sahifalarni yuklaydi. Sahifaga o'tish, kattalashtirish, kitob ichida qidirish, o'qish joyini eslab qolish, sahifadan Anki kartasi yaratish |

Skanerlangan (faqat rasmdan iborat) PDF'larda matn qatlami bo'lmaydi: kitob o'qiladi, lekin ichida qidirish ishlamaydi (OCR yo'q).

**Railway uchun:** `/data` ga volume ulang va hajmini barcha kitoblar va rasmlar umumiy hajmidan kattaroq qiling. Admin → **Saqlash joyi** bo'limida bo'sh joy va ishlatilgan hajm ko'rinadi.

## Tuzilishi

```
backend/            FastAPI + SQLAlchemy 2.0 (async) + aiogram 3
  app/models.py     ma'lumotlar bazasi modellari
  app/services/     scoring, sm2, inventory (FEFO), tandem, biopsy workflow
  app/routers/      auth, admin, inventory, biopsies, images, atlas, academy
  app/bot/          Telegram bot: tugmali menyu, bildirishnomalar, inline tasdiqlash, /login
  app/seed/         atlas (JSON), inventar, akademiya, shablonlar
  migrations/       Alembic migratsiyalari (ilova ishga tushganda avtomatik qo'llanadi)
  tests/            56 ta test (SQLite va PostgreSQL)
frontend/           React 18 + Vite + Tailwind 4 + lucide-react
Dockerfile          monolit konteyner (frontend build + API + bot [+ PostgreSQL])
railway.json
```

## Lokal ishga tushirish

```bash
# Backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r backend/requirements-dev.txt
cp .env.example .env     # DATABASE_URL, BOT_TOKEN va boshqalar
cd backend && DEV_MODE=1 SEED_DEMO=1 uvicorn app.main:app --reload

# Frontend (boshqa terminalda): http://localhost:5173, /api proxy orqali :8000 ga boradi
cd frontend && npm ci && npm run dev
```

`DEV_MODE=1` bo'lsa, login sahifasida har bir rol uchun "Dev" tugmalari chiqadi. **Production'da hech qachon yoqmang.**

Testlar:

```bash
cd backend
pytest                                                         # SQLite
TEST_DATABASE_URL=postgresql+asyncpg://postgres@localhost/pathouz_test pytest   # PostgreSQL
```

## Railway'ga joylash

1. Repozitoriyni Railway'ga ulang, u `Dockerfile` va `railway.json` ni o'zi topadi.
2. **Tavsiya etiladi:** Railway PostgreSQL plaginini qo'shing. U `DATABASE_URL` ni o'zi o'rnatadi. Bu holda image'ni `EMBEDDED_PG=0` build argumenti bilan kichikroq qilish mumkin.
3. `DATABASE_URL` berilmasa, konteyner ichki PostgreSQL'ni ishga tushiradi. Bu holda `/data` ga **volume** ulang, aks holda har deploy'da ma'lumotlar yo'qoladi.
4. O'zgaruvchilar: `BOT_TOKEN`, `BOT_USERNAME`, `WEBAPP_URL` (Railway bergan HTTPS manzil), `SUPER_ADMIN_IDS`, `JWT_SECRET` (uzun tasodifiy qator).
5. @BotFather'da Mini App'ga `WEBAPP_URL` ni bering. Bot ishga tushganda menyu tugmasini o'zi o'rnatadi.

## Kirish va rollar

- Telegram ichida: `initData` imzosi tekshiriladi, keyin JWT beriladi.
- Brauzerda: botga `/login` yozing, 10 daqiqa amal qiladigan bir martalik havola keladi.
- Yangi foydalanuvchi **🎓 Rezident** bo'lib kiradi. `SUPER_ADMIN_IDS` dagilar **👑 Super Admin** bo'ladi va Admin → Xodimlar bo'limida boshqalarga rol beradi.

| | Atlas / Academy | Biopsiyalar | Tasdiqlash, skoring, konsilium | Inventar | Admin |
|---|:-:|:-:|:-:|:-:|:-:|
| 👑 Super Admin | ✓ | ✓ | ✓ | ✓ | ✓ |
| 👨‍⚕️ Patolog | ✓ | ✓ | ✓ | ko'rish | |
| 🧪 Laborant | ✓ | ✓ (bemor ismi yashirin) | | ✓ | |
| 🎓 Rezident | ✓ | | | | |

## Muhim eslatmalar

- **Zaxira yechish poygaga chidamli.** Holat shartli `UPDATE` bilan band qilinadi, lotlar `quantity > 0` sharti bilan atomik kamaytiriladi va qatorlar `FOR UPDATE` bilan qulflanadi. Parallel tasdiqlashlar testlarda tekshirilgan.
- **Smart Tandem** faqat klinik juftliklar ro'yxatidagi (`tandem_with`) markerlarni taklif qiladi. Inventar holati faqat ularning tartibini o'zgartiradi, ko'rsatma o'ylab topilmaydi. Yakuniy qaror patologda.
- **Laboratoriya pasportlari namuna protokollar.** Har bir laboratoriya ularni o'z platformasida validatsiya qilishi shart.
- **Atlas va viktorina matnlari** loyiha uchun mustaqil yozilgan. Klinik foydalanishdan oldin patolog-mutaxassis ko'rib chiqishi kerak.
- **Smart Reader'dagi kitob** loyihaning o'z o'quv konspekti. WHO Blue Books, Dabbs va boshqa mualliflik huquqi bilan himoyalangan matnlarni faqat muassasada huquqi bo'lsa `POST /api/books/import` orqali qo'shing.
- **Telegram xabarlarida** faqat holat kodi ko'rsatiladi, bemor ismi chiqmaydi.
- **Migratsiyalar:** Alembic. Model o'zgarsa: `cd backend && alembic revision --autogenerate -m "..."`. Test `test_migrations_match_models` migratsiyalar modellarga mos kelishini tekshiradi.
- **Chop etish:** biopsiya hisoboti va 25×25 mm stakan stikerlari 5 daqiqalik imzolangan havola orqali tizim brauzerida ochiladi (Telegram ichida chop etib bo'lmaydi), u yerda "Chop etish → PDF sifatida saqlash" ishlaydi.
