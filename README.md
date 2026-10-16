# Kurs uchun Telegram bot

aiogram 3 + SQLAlchemy (async) + APScheduler. Baza: Railway'da PostgreSQL, lokal testda SQLite.

## Papkalar tuzilishi

```
bot.py              — ishga tushirish fayli
config.py           — ENV o'zgaruvchilarni o'qish
texts.py            — BARCHA matnlar (shu yerdan tahrirlanadi)
filters.py          — admin filtri
middlewares.py      — baza sessiyasi
db/                 — jadvallar (models.py) va so'rovlar (repo.py)
services/           — biznes-mantiq: to'lov, obuna, guruhlar, tarqatish, hisobotlar
handlers/           — Telegram xabarlariga javoblar
web/                — web admin-panel (server.py, API, static/ — sahifa dizayni va JS)
keyboards/          — tugmalar
scheduler/jobs.py   — har kuni 10:00 dagi vazifa
```

---

## 1. Telegram'da tayyorgarlik (bir marta)

1. **Bot yarating:** @BotFather → `/newbot` → token oling (`BOT_TOKEN`).
2. **Admin ID:** @userinfobot ga yozing — u sizning raqamli ID ingizni beradi (`ADMIN_IDS`).
   Har bir admin botga kamida bir marta `/start` bosishi kerak, aks holda bot unga xabar yubora olmaydi.
3. **Kanal ID sini bilish:** kompyuterda https://web.telegram.org/a/ ni oching, kanalni oching —
   manzil satrida `#-100...` ko'rinadi. Shu raqam (minus bilan) — kanal ID si.
4. **Botni admin qiling** — bepul kanal, pullik kanal va har bir kurs guruhida:
   - «Foydalanuvchilarni qo'shish / havola orqali taklif qilish» ✅
   - «Foydalanuvchilarni bloklash (ban)» ✅
5. **Pullik kanal va guruhlar yopiq (private)** bo'lsin. Bot o'zi shaxsiy havola yaratadi.
6. Kurs guruhlarida «anonim admin» rejimini o'chiring (aks holda `/addgroup` sizni admin deb tanimaydi).

---

## 2. Railway'ga joylash (qadam-baqadam)

### A. Kodni GitHub'ga yuklash
1. https://github.com da ro'yxatdan o'ting (bepul).
2. Yuqori o'ngdagi **«+» → New repository** → nom bering (masalan `kurs-bot`) → **Private** ni tanlang → **Create repository**.
3. Ochilgan sahifada **«uploading an existing file»** havolasini bosing.
4. Shu papkadagi barcha fayl va papkalarni sudrab tashlang. **`.env` faylini va `.venv` papkasini YUKLAMANG!**
5. **Commit changes** tugmasini bosing.

### B. Railway'da loyiha
1. https://railway.app → GitHub orqali kiring.
2. **New Project → Deploy from GitHub repo** → `kurs-bot` ni tanlang.
   (Birinchi marta Railway'ga GitHub'ga ruxsat berish so'raladi — «Configure GitHub App» → repo'ni tanlang.)
3. Birinchi deploy xato bilan tugashi normal — hali o'zgaruvchilar kiritilmagan.

### C. PostgreSQL qo'shish
1. Loyiha ichida **«+ Create» (yoki «New») → Database → Add PostgreSQL**.
2. Bir necha soniyada «Postgres» bloki paydo bo'ladi.

### D. O'zgaruvchilar (Variables)
1. Bot servisini (kurs-bot) bosing → **Variables** bo'limi → **Raw Editor**.
2. Quyidagini qo'yib, o'z qiymatlaringiz bilan to'ldiring:

   Faqat shu **4 tasi majburiy**:

```
BOT_TOKEN=...
ADMIN_IDS=123456789
DATABASE_URL=${{Postgres.DATABASE_URL}}
ADMIN_PANEL_PASSWORD=bu-yerga-kuchli-parol
```

   - `DATABASE_URL=${{Postgres.DATABASE_URL}}` ni aynan shunday yozing — Railway o'zi bazaga ulaydi.
   - `ADMIN_PANEL_PASSWORD` — web-panelga birinchi kirish paroli (kamida 12 belgi, harf+raqam). Keyin uni panelda o'zgartirsa bo'ladi.
   - Qolganlari (kanal ID lari, havola, karta, narxlar, matnlar) **web-panel → ⚙️ Sozlamalar** da qulay kiritiladi —
     bu yerda yozish shart emas. Agar xohlasangiz, `.env.example` dagi nomlar bilan bu yerga ham yozish mumkin;
     panelda kiritilgan qiymat ustun bo'ladi.
3. **Update Variables** → Railway avtomatik qayta deploy qiladi.

### E. Tekshirish
1. Servis → **Deployments → View logs**. `Bot ishga tushdi` yozuvi chiqsa — tayyor.
2. Agar bot kanalda admin bo'lmasa, adminlarga «⚠️ Diqqat!» xabari keladi.
3. **Muhim:** Settings → Replicas = **1** bo'lsin (ikkita nusxa bir vaqtda ishlasa, Telegram xato beradi).

### F. Web admin-panelni ochish
1. Bot servisi → **Settings → Networking → Generate Domain** tugmasini bosing.
   (Port so'ralsa, bo'sh qoldiring yoki loglardagi «Web admin-panel ishga tushdi: port …» raqamini yozing.)
2. Railway `https://kurs-bot-production-xxxx.up.railway.app` ko'rinishidagi manzil beradi.
3. Shu manzilni brauzerda (telefon yoki kompyuter) oching → `ADMIN_PANEL_PASSWORD` parolini kiriting.
4. Manzilni xatcho'pga (bookmark) saqlang. Kirish 7 kun eslab qolinadi.

### G. Sozlamalarni kiritish (⚙️ Sozlamalar)
1. Botni bepul va pullik kanalga **admin** qiling — bot sizga Telegram'da kanal nomi va **ID** sini yozib yuboradi.
   (Yoki kanaldan istalgan postni botga forward qiling — bot ID ni aytadi.)
2. Panel → **⚙️ Sozlamalar** → «Kanallar va adminlar»: ID ni qo'ying → **🔍 Tekshirish** →
   «✅ bot admin, huquqlari yetarli» chiqsa → **💾 Saqlash**.
3. «To'lov»: karta raqami, egasi, pullik kanal narxi → Saqlash.
4. «Online kurs tariflari»: narx va tavsiflar, Senior joylar soni → Saqlash.
5. «Bot matnlari»: bepul sovg'a, bepul dars havolasi, «Men haqimda» → «🧪 Menga yuborib ko'rish» → Saqlash.
6. Hammasi **darhol** kuchga kiradi — botni qayta ishga tushirish shart emas.

Har bir maydon yonida qiymat qayerdan kelayotgani yozilgan: «Panelda kiritilgan» / «Railway Variables'dan» / «Kiritilmagan».
«↺ Railway qiymatiga qaytarish» — panel qiymatini o'chirib, Railway'dagisiga qaytaradi.

### Kodni yangilash
GitHub'da faylni o'zgartirsangiz (masalan `texts.py`), Railway avtomatik qayta joylaydi.

---

## 3. Lokal test (ixtiyoriy)

```bash
python -m venv .venv
```
```bash
.venv\Scripts\pip install -r requirements.txt
```
`.env.example` ni `.env` deb nusxalang, qiymatlarni to'ldiring (`DATABASE_URL` bo'sh — SQLite ishlatiladi), so'ng:
```bash
.venv\Scripts\python bot.py
```
⚠️ Bir token bilan bir vaqtda faqat bitta bot ishlay oladi — lokal testda Railway'dagi servisni to'xtatib turing
yoki test uchun alohida bot yarating.

---

## 4. Web admin-panel

To'rtta bo'lim (⚙️ Sozlamalar — yuqoridagi 2-G qismda):

**👥 Foydalanuvchilar**
- Ism, telefon, @username, segment, manba, ro'yxatdan o'tgan sana.
- **Bepul kanal:** ✅ obuna / ❌ obuna emas / — tekshirilmagan.
- **Pullik kanal:** faol obuna (qachongacha), tugagan yoki yo'q; kanalda hozir bormi.
- **Kurs guruhi:** qaysi tarif, qaysi guruhga joylangan, guruhga qo'shilganmi yoki guruh kutyapti.
- Filtrlar: bepul kanal, pullik kanal, guruh, segment; qidiruv (ism / telefon / ID).
- 🔄 (qator yonida) — shu odamning a'zoligini hozir Telegram'dan tekshiradi.
  «A'zolikni yangilash» — hammani tekshiradi (1000 kishi ≈ 2 daqiqa).
- 📥 Excel — barcha ma'lumot (kanal, guruh ustunlari bilan).

> Telegram botga «kim kanaldan chiqdi» deb o'zi xabar bermaydi. Shuning uchun «Bepul kanal» ustuni
> oxirgi tekshiruv natijasini ko'rsatadi (sanasi ostida yozilgan). Aniq holat uchun 🔄 ni bosing.

**💬 Chat**
- Botga yozgan har bir foydalanuvchi shu yerda chiqadi: «Admin bilan bog'lanish», AI agent buyurtmasi
  yoki shunchaki botga yozilgan istalgan xabar (rasm, ovozli xabar, fayl ham).
- O'qilmaganlar soni qizil belgida. Sahifa har 3 soniyada yangilanadi.
- Javob yozing (Enter — yuborish), 📎 bilan rasm yoki fayl biriktiring. Javob foydalanuvchiga
  «📩 Admin javobi» ko'rinishida boradi.
- Foydalanuvchilar jadvalidagi 💬 tugmasi ham shu odam bilan chatni ochadi (birinchi bo'lib yozish mumkin).

**📝 Kontent**
1. Rasm/video qo'shing (10 tagacha — albom bo'ladi).
2. Matn yozing. Asboblar: **qalin**, *kursiv*, tagiga chizilgan, o'chirilgan, `kod`, yashirin matn (spoiler), iqtibos, havola, emoji.
3. **«Aa Ishlov berish»** — belgilangan matnga (yoki butun matnga):
   KATTA / kichik harflar, Har So'z Bosh Harfda, gap boshini katta qilish, **Lotin ↔ Кирилл**,
   oʻ / gʻ va tutuq belgisini to'g'rilash, «qo'shtirnoq» va — tire, ortiqcha bo'shliqlarni tozalash,
   #heshteg, qatorlarga • yoki 1. 2. 3. qo'yish.
4. Tugma qo'shing (matn + havola).
5. O'ng tomonda post Telegram'da qanday ko'rinishi chiqadi. Qoralama brauzerda avtomatik saqlanadi.
6. **🧪 Menga test yuborish** — avval o'zingizga (adminlarga) yuborib ko'ring.
7. **📤 Joylash…** — qayerga joylashni so'raydi: bepul kanal, pullik kanal, kurs guruhlari va/yoki
   bot foydalanuvchilari (hammaga / segment / xarid qilmaganlar / pullik obunachilar). Bir nechtasini birga tanlash mumkin.
8. «Joylanganlar tarixi»da nima, qachon, qayerga ketgani ko'rinadi.

---

## 5. Admin buyruqlari (Telegram ichida)

| Buyruq | Vazifasi |
|---|---|
| `/admin` yoki «⚙️ Admin panel» | Statistika, Excel, tarqatish, kutilayotgan to'lovlar, qidiruv, guruhlar |
| `/setgift` | Bepul sovg'a (5 ta prompt) matni |
| `/setlesson` | «Bepul dars» matni |
| `/setabout` | «Men haqimda» matni |
| `/settariff` | Tarif narxi va tavsifi |
| `/setseniorlimit 20` | Senior joylar soni |
| `/addgroup basic 20` | Guruh qo'shish (guruh ichida yoziladi). Tarif: basic/middle/senior/any |
| `/groups` | Guruhlar ro'yxati, yoqish/o'chirish |
| `/cancel` | Joriy amalni bekor qilish |

Matnlarda Telegram formatlashi (qalin, kursiv, havola) saqlanadi.

---

## 6. Test qilish ro'yxati

**Web-panel**
- [ ] Noto'g'ri parol → «Parol noto'g'ri». To'g'ri parol → panel ochiladi.
- [ ] Test akkauntda ro'yxatdan o'ting → «Foydalanuvchilar»da paydo bo'ladi, «Bepul kanal: ✅ Obuna».
- [ ] Test akkaunt bepul kanaldan chiqsin → 🔄 bosing → «❌ Obuna emas».
- [ ] Pullik kanal to'lovi tasdiqlangach → «💎 … gacha», kanalga qo'shilgach «Kanalda: ✅ bor».
- [ ] Kurs to'lovi tasdiqlangach → «Kurs guruhi» ustunida tarif va guruh nomi.
- [ ] Test akkauntdan botga «Salom» yozing → «Chat»da qizil belgi bilan chiqadi. Javob yozing → Telegram'ga keladi.
- [ ] Chatda rasm yuboring → foydalanuvchiga rasm boradi.
- [ ] Kontent: rasm + matn + tugma → «Menga test yuborish» → Telegram'ingizda tekshiring.
- [ ] «Lotin → Кирилл» va qaytarish, «#heshteg», «•» ni sinang.
- [ ] «Joylash…» → bepul kanalni tanlang → post kanalda chiqadi, tarixda ko'rinadi.

**Sozlamalar**
- [ ] Botni yangi kanalga admin qiling → Telegram'da «✅ Bot … ga admin qilindi, ID: …» xabari keladi.
- [ ] Kanal postini botga forward qiling → bot kanal ID sini yozadi.
- [ ] Noto'g'ri karta (masalan 12 raqam) → «Karta raqami 16 ta raqamdan…» xatosi, hech narsa saqlanmaydi.
- [ ] Karta raqamini o'zgartiring → botda «💎 Pullik kanal» bosing → yangi karta ko'rinadi (qayta ishga tushirmasdan).
- [ ] Basic narxini o'zgartiring → «📚 Online kurs»da yangi narx.
- [ ] Bepul sovg'a matnini o'zgartiring → «Menga yuborib ko'rish» → Telegram'da tekshiring.
- [ ] Parolni o'zgartiring → boshqa brauzerda eski parol bilan kira olmaysiz.


Test uchun ikkinchi Telegram akkaunt (yoki do'stingiz) kerak — «foydalanuvchi» sifatida.

**Ro'yxatdan o'tish**
- [ ] `https://t.me/BOT_USERNAME?start=ig` orqali kiring → Excel'da «Manba» = `ig`.
- [ ] Ism o'rniga stiker yuboring → bot ism so'raydi.
- [ ] Raqamni qo'lda yozing → bot tugmani bosishni so'raydi.
- [ ] Boshqa odam kontaktini yuboring → «Bu sizning raqamingiz emas».
- [ ] Segment tanlang.
- [ ] Kanalga obuna bo'lmay «Tekshirish» → ogohlantirish. Obuna bo'lib «Tekshirish» → sovg'a + menyu.
- [ ] «Biznes egasi» tanlaganda menyuda «🤖 AI agent buyurtma qilish» bor, boshqalarda yo'q.
- [ ] Qayta `/start` → «Qaytganingizdan xursandmiz», ro'yxat qaytadan so'ralmaydi.

**Pullik kanal**
- [ ] «💎 Pullik kanal» → karta raqami ustiga bosilsa nusxalanadi.
- [ ] «Chekni yuborish» → matn yuboring → bot rasm/fayl so'raydi. Rasm yuboring → «qabul qilindi».
- [ ] Barcha adminlarga chek + ma'lumot + [Tasdiqlash] [Rad etish] keladi.
- [ ] Kutilayotgan chek bor paytda yana «Chekni yuborish» → «avvalgi chek tekshirilmoqda».
- [ ] Rad etish → «Pul tushmagan» → foydalanuvchiga sabab keladi, admin xabarida «RAD ETILDI».
- [ ] Rad etish → «Boshqa» → sabab yozing → foydalanuvchiga shu matn keladi.
- [ ] Yangi chek → Tasdiqlash → foydalanuvchiga havola keladi. Ikkinchi admin ham bossa → «allaqachon ko'rib chiqilgan».
- [ ] Havola orqali «Qo'shilish so'rovi» → bot avtomatik qabul qiladi.
- [ ] Shu havolani boshqa akkauntdan ochib so'rov yuboring → rad etiladi.
- [ ] Uzaytirish: faol obuna bilan yana to'lov → tugash sanasi +30 kun («Pullik kanal» bo'limida ko'rinadi).

**Obuna nazorati** (10:00 ni kutmasdan tekshirish)
- [ ] Admin panel → Qidirish → foydalanuvchi → «Obunani bekor qilish» → kanaldan chiqariladi, keyin yana havola bilan qaytishi mumkin.
- [ ] Ertasi kuni 10:00 da adminlarga «Kunlik hisobot» keladi.
- [ ] Eslatmalarni tekshirish: obunani «➕ 7 kun» bilan bering (kanalga kirmasdan), 4-5 kundan keyin 10:00 da 3 kunlik eslatma keladi.

**Online kurs**
- [ ] «📚 Online kurs» → 3 ta tarif narxi bilan. `/settariff` bilan narxni o'zgartiring → yangilanadi.
- [ ] Guruh qo'shilmagan holda tarif to'lovini tasdiqlang → foydalanuvchiga «tez orada havola», adminga «joy yo'q».
- [ ] Guruhga botni admin qiling, guruhda `/addgroup senior 20` → kutayotgan foydalanuvchiga havola avtomatik ketadi.
- [ ] `/setseniorlimit 1` → bitta Senior xariddan keyin tarif «Joylar tugadi» ko'rinadi.

**Admin panel**
- [ ] Statistika: lidlar, segmentlar, manbalar, to'lovlar, guruhlar.
- [ ] «Lidlar (Excel)» → .xlsx fayl keladi.
- [ ] Tarqatish: «Hammaga» → rasm + izoh → tugma `Batafsil | https://t.me/...` → oldindan ko'rish → Yuborish → hisobot.
- [ ] Botni bloklagan akkauntga tarqatish → hisobotda «Bloklaganlar» va statistikada ko'rinadi.
- [ ] «Admin bilan bog'lanish» → foydalanuvchi yozadi → admin «Javob berish» → javob foydalanuvchiga boradi.

---

## 7. Bilish kerak bo'lgan narsalar

- Web-panel bot bilan bitta Railway servisida ishlaydi — alohida to'lov yoki servis kerak emas.
- Panelga kirish uchun bitta umumiy parol bor. Uni panelda o'zgartirsangiz, boshqa qurilmalardagi kirishlar bekor bo'ladi.
  Panel parolini unutsangiz: Railway → Postgres → Data → `settings` jadvalidan `panel_password_hash` qatorini o'chiring —
  shunda yana `ADMIN_PANEL_PASSWORD` ishlaydi.
  10 marta noto'g'ri parol kiritilsa, o'sha IP 15 daqiqaga bloklanadi.

- Bot qayta ishga tushsa, foydalanuvchi o'rtada qolgan bosqich (masalan chek kutish) eslab qolinmaydi — tugmani qayta bosadi. Baza ma'lumotlari saqlanib qoladi.
- Kirish havolasi 24 soat amal qiladi. Muddati o'tsa: foydalanuvchi «Pullik kanal» / «Online kurs» bo'limidagi «🔗 ... kirish havolasi» tugmasini bosadi, yoki admin qidiruvdan «Kanal havolasini yuborish»ni bosadi.
- Guruh a'zolari soni bot havola bergan paytda band qilinadi (bitta joyga ikki kishi tushmasligi uchun).
- Xatolar Railway loglariga yoziladi, jiddiy xatolar adminlarga xabar qilib yuboriladi.
