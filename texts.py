"""Botdagi BARCHA matnlar shu faylda.

Matnni o'zgartirmoqchi bo'lsangiz, faqat qo'shtirnoq ichidagi yozuvni o'zgartiring.
{name}, {price} kabi jingalak qavsli so'zlarni o'chirmang — ular o'rniga bot ma'lumot qo'yadi.
Formatlash: <b>qalin</b>, <i>kursiv</i>, <code>nusxalanadigan</code>.
"""

# ============================================================
# TUGMALAR
# ============================================================
BTN_COURSE = "📚 Online kurs"
BTN_PAID = "💎 Pullik kanal"
BTN_FREE_LESSON = "🎁 Bepul dars"
BTN_ABOUT = "👤 Men haqimda"
BTN_CONTACT = "✉️ Admin bilan bog'lanish"
BTN_AI_AGENT = "🤖 AI agent buyurtma qilish"
BTN_ADMIN = "⚙️ Admin panel"

MENU_BUTTONS = {BTN_COURSE, BTN_PAID, BTN_FREE_LESSON, BTN_ABOUT, BTN_CONTACT, BTN_AI_AGENT, BTN_ADMIN}

BTN_SEND_PHONE = "📱 Raqamni yuborish"
BTN_CANCEL = "❌ Bekor qilish"
BTN_GO_CHANNEL = "📢 Kanalga o'tish"
BTN_CHECK_SUB = "✅ Tekshirish"
BTN_SEND_RECEIPT = "📤 Chekni yuborish"
BTN_RENEW = "🔄 Uzaytirish"
BTN_JOIN_CHANNEL = "🔗 Kanalga qo'shilish"
BTN_JOIN_GROUP = "🔗 Guruhga qo'shilish"
BTN_GET_CHANNEL_LINK = "🔗 Kanalga kirish havolasi"
BTN_GET_GROUP_LINK = "🔗 Guruhga kirish havolasi"
BTN_BACK = "⬅️ Ortga"
BTN_APPROVE = "✅ Tasdiqlash"
BTN_REJECT = "❌ Rad etish"
BTN_REPLY = "↩️ Javob berish"
BTN_SKIP = "⏭ O'tkazib yuborish"
BTN_SEND = "🚀 Yuborish"

# ============================================================
# LUG'ATLAR
# ============================================================
SEGMENTS = {"smm": "SMM mutaxassisi", "biz": "Biznes egasi", "learn": "O'rganuvchi"}

TARIFF_NAMES = {"basic": "Basic", "middle": "Middle", "senior": "Senior"}
GROUP_TARIFFS = {"basic": "Basic", "middle": "Middle", "senior": "Senior", "any": "Har qanday tarif"}

PRODUCT_TITLES = {
    "paid_channel": "Pullik kanal (30 kun)",
    "tariff_basic": "Online kurs — Basic",
    "tariff_middle": "Online kurs — Middle",
    "tariff_senior": "Online kurs — Senior",
}

REJECT_REASONS = {"nomoney": "Pul tushmagan", "wrongsum": "Noto'g'ri summa", "other": "Boshqa"}

PAYMENT_STATUSES = {"pending": "⏳ Kutilmoqda", "approved": "✅ Tasdiqlangan", "rejected": "❌ Rad etilgan"}

# ============================================================
# RO'YXATDAN O'TISH (/start)
# ============================================================
WELCOME = (
    "Assalomu alaykum! 👋\n\n"
    "Botimizga xush kelibsiz! Bu yerda sizni foydali materiallar, online kurs "
    "va yopiq kanalimiz kutmoqda.\n\n"
    "Boshlash uchun <b>ism va familiyangizni</b> yozing:"
)
WELCOME_BACK = "Qaytganingizdan xursandmiz, <b>{name}</b>! 👋\nQuyidagi menyudan kerakli bo'limni tanlang."
ASK_NAME_AGAIN = "Iltimos, ism va familiyangizni matn ko'rinishida yozing (masalan: <i>Aziz Karimov</i>)."
ASK_PHONE = (
    "Tanishganimdan xursandman, <b>{name}</b>! 😊\n\n"
    "Endi telefon raqamingizni yuboring. Buning uchun pastdagi "
    "<b>«📱 Raqamni yuborish»</b> tugmasini bosing."
)
PHONE_USE_BUTTON = "Iltimos, raqamni qo'lda yozmang — pastdagi <b>«📱 Raqamni yuborish»</b> tugmasini bosing 👇"
PHONE_NOT_OWN = "Bu sizning raqamingiz emas. Iltimos, <b>o'z</b> raqamingizni tugma orqali yuboring 👇"
PHONE_SAVED = "✅ Raqamingiz saqlandi."
ASK_SEGMENT = "Siz kimsiz? Quyidagilardan birini tanlang 👇"
SEGMENT_CHOSEN = "Tanlovingiz: <b>{segment}</b> ✅"
USE_BUTTONS = "Iltimos, yuqoridagi tugmalardan birini bosing 👆"
ASK_SUBSCRIBE = (
    "Oxirgi qadam! 🎁\n\n"
    "Bepul sovg'ani olish uchun bepul kanalimizga obuna bo'ling, so'ng "
    "<b>«✅ Tekshirish»</b> tugmasini bosing."
)
NOT_SUBSCRIBED = "Siz hali kanalga obuna bo'lmagansiz. Avval obuna bo'ling, so'ng «Tekshirish»ni bosing."
SUB_CONFIRMED = "✅ Obuna tasdiqlandi! Mana sizga va'da qilingan sovg'a 👇"
REG_DONE = "✅ Ro'yxatdan o'tdingiz! Mana sizga va'da qilingan sovg'a 👇"
ADMIN_FREE_CHANNEL_MISSING = (
    "⚠️ <b>Bepul kanal sozlanmagan.</b> Foydalanuvchilar obuna bosqichisiz ro'yxatdan o'tkazilmoqda.\n"
    "Web-panel → Sozlamalar → «Bepul kanal ID si» ni kiriting."
)
ADMIN_FREE_LINK_MISSING = (
    "⚠️ <b>Bepul kanal havolasi topilmadi</b> — «Kanalga o'tish» tugmasi ko'rsatilmayapti.\n"
    "Web-panel → Sozlamalar → «Bepul kanal havolasi» ni kiriting (https://t.me/...)."
)
ADMIN_FREE_CHECK_FAILED = (
    "⚠️ <b>Bot bepul kanalga obunani tekshira olmayapti</b> — foydalanuvchilar tekshiruvsiz o'tkazilmoqda.\n"
    "Botni bepul kanalga admin qiling va web-panel → Sozlamalar'da kanal ID sini «Tekshirish» bilan tekshiring."
)
MENU_HINT ="Quyidagi menyudan kerakli bo'limni tanlang 👇"
NEED_START = "Avval ro'yxatdan o'ting: /start buyrug'ini bosing."
CANCELLED = "Bekor qilindi."

# ============================================================
# STANDART MATNLAR (admin buyruqlar orqali o'zgartiradi)
# ============================================================
DEFAULT_GIFT = (
    "🎁 <b>Sizga sovg'a: 5 ta foydali prompt</b>\n\n"
    "1️⃣ <b>Kontent-reja</b>\n"
    "<code>Sen tajribali SMM mutaxassisisan. [soha] bo'yicha Instagram sahifa uchun 30 kunlik "
    "kontent-reja tuz: har kun uchun mavzu, format (reels/post/stories) va qisqa g'oya.</code>\n\n"
    "2️⃣ <b>Sotuvchi matn</b>\n"
    "<code>[mahsulot] uchun AIDA formulasi asosida 3 xil sotuvchi post matnini yoz. "
    "Auditoriya: [auditoriya]. Ohang: samimiy.</code>\n\n"
    "3️⃣ <b>Reels ssenariysi</b>\n"
    "<code>[mavzu] bo'yicha 30 soniyalik Reels ssenariysini yoz: birinchi 3 soniyadagi hook, "
    "asosiy qism va harakatga chaqiruv.</code>\n\n"
    "4️⃣ <b>Mijoz e'tirozlari</b>\n"
    "<code>[mahsulot] sotishda mijozlar aytadigan 10 ta e'tirozni va har biriga ishonchli "
    "javobni yoz.</code>\n\n"
    "5️⃣ <b>Raqobatchi tahlili</b>\n"
    "<code>[raqobatchi sahifasi] kontentini tahlil qil: kuchli va zaif tomonlari, "
    "men undan qanday ustun bo'lishim mumkin — 5 ta aniq tavsiya ber.</code>"
)
DEFAULT_LESSON = (
    "🎁 <b>Bepul dars</b>\n\n"
    "Bepul darsni quyidagi havola orqali ko'rishingiz mumkin:\n"
    "👉 (havolani admin /setlesson buyrug'i orqali qo'shadi)"
)
DEFAULT_ABOUT = (
    "👤 <b>Men haqimda</b>\n\n"
    "(Bu matnni admin /setabout buyrug'i orqali o'zgartiradi.)"
)
DEFAULT_TARIFF_DESC = {
    "basic": "✅ Video darslar\n✅ Uy vazifalari\n✅ Umumiy guruhda savol-javob",
    "middle": "✅ Basic tarifidagi hammasi\n✅ Uy vazifalarini tekshirish\n✅ Haftalik jonli efirlar",
    "senior": "✅ Middle tarifidagi hammasi\n✅ Shaxsiy mentorlik\n✅ Real loyiha ustida ishlash\n"
              "⚠️ Joylar soni cheklangan",
}

# ============================================================
# ASOSIY MENYU BO'LIMLARI
# ============================================================
COURSE_INTRO = "📚 <b>Online kurs</b>\n\nO'zingizga mos tarifni tanlang 👇\n"
COURSE_TARIFF_LINE = "\n<b>{title}</b> — {price} so'm{full}"
SEATS_FULL = "Joylar tugadi"
SEATS_FULL_ALERT = "Afsuski, Senior tarifida joylar tugadi 😔"
TARIFF_DETAIL = (
    "📚 <b>{title}</b>\n\n"
    "{desc}\n\n"
    "💰 Narxi: <b>{price} so'm</b>\n\n"
    "💳 To'lov uchun karta:\n<code>{card}</code>\n👤 {holder}\n"
    "<i>(Karta raqamini nusxalash uchun ustiga bosing)</i>\n\n"
    "To'lovni amalga oshirgach, <b>«📤 Chekni yuborish»</b> tugmasini bosing."
)
TARIFF_BUTTON = "{title} — {price} so'm"
TARIFF_BUTTON_FULL = "{title} — Joylar tugadi"

PAID_CHANNEL_INFO = (
    "💎 <b>Pullik kanal</b>\n\n"
    "Yopiq kanalda eng foydali materiallar, tayyor promptlar va amaliy darslar joylanadi.\n\n"
    "💰 Narxi: <b>{price} so'm / 30 kun</b>\n\n"
    "💳 To'lov uchun karta:\n<code>{card}</code>\n👤 {holder}\n"
    "<i>(Karta raqamini nusxalash uchun ustiga bosing)</i>\n\n"
    "To'lovni amalga oshirgach, <b>«📤 Chekni yuborish»</b> tugmasini bosing."
)
PAID_CHANNEL_ACTIVE = (
    "\n\n✅ Sizda faol obuna bor. Tugash sanasi: <b>{end}</b>\n"
    "Uzaytirsangiz, 30 kun shu sanaga qo'shiladi."
)

ASK_SUPPORT_MESSAGE = "✍️ Savolingiz yoki xabaringizni yozing — adminga yetkazaman:"
SUPPORT_SENT = "✅ Xabaringiz adminga yuborildi. Tez orada javob beramiz."
ASK_AGENT_ORDER = (
    "🤖 <b>AI agent buyurtma qilish</b>\n\n"
    "Biznesingiz va qanday AI agent kerakligini batafsil yozing "
    "(masalan: «Instagram'da mijozlarga avtomatik javob beradigan bot»):"
)
AGENT_ORDER_SENT = "✅ Arizangiz qabul qilindi! Mutaxassisimiz siz bilan tez orada bog'lanadi."
ONLY_TEXT = "Iltimos, xabarni matn ko'rinishida yozing."
ADMIN_REPLY_HEADER = "📩 <b>Admin javobi:</b>"
CHAT_RECEIVED = "✅ Xabaringiz adminga yetkazildi. Javob shu yerga keladi."
CHAT_AGENT_PREFIX = "🤖 AI agent buyurtmasi:\n"

# ============================================================
# TO'LOV (foydalanuvchi tomoni)
# ============================================================
SEND_RECEIPT_PROMPT = (
    "🧾 <b>{product}</b>\n"
    "💰 Summa: <b>{price} so'm</b>\n"
    "💳 Karta: <code>{card}</code> ({holder})\n\n"
    "To'lov chekining <b>rasmini</b> (skrinshot) yoki <b>faylini</b> shu yerga yuboring.\n"
    "Bekor qilish uchun «❌ Bekor qilish» tugmasini bosing."
)
RECEIPT_WRONG_TYPE = "Iltimos, chekni <b>rasm</b> yoki <b>fayl</b> ko'rinishida yuboring."
RECEIPT_RECEIVED = (
    "✅ Chekingiz qabul qilindi va adminga yuborildi.\n"
    "Tekshiruvdan so'ng sizga xabar beramiz (odatda bir necha soat ichida)."
)
PAYMENT_ALREADY_PENDING = "Sizning avvalgi chekingiz hali tekshirilmoqda. Iltimos, natijani kuting."

PAID_APPROVED = (
    "✅ <b>To'lovingiz tasdiqlandi!</b>\n\n"
    "Obunangiz <b>{end}</b> gacha amal qiladi.\n\n"
    "Pastdagi tugmani bosib kanalga qo'shilish so'rovini yuboring — bot uni avtomatik tasdiqlaydi.\n"
    "⚠️ Havola 24 soat amal qiladi va faqat siz uchun."
)
PAID_EXTENDED = "✅ <b>To'lovingiz tasdiqlandi!</b> Obunangiz uzaytirildi.\nYangi tugash sanasi: <b>{end}</b>"
CHANNEL_LINK = (
    "🔗 Kanalga kirish havolasi tayyor.\n"
    "⚠️ Havola 24 soat amal qiladi va faqat siz uchun."
)
ALREADY_IN_CHANNEL = "Siz allaqachon kanaldasiz ✅"
NO_ACTIVE_SUB = "Sizda faol obuna yo'q."
COURSE_APPROVED = "✅ <b>To'lovingiz tasdiqlandi!</b> Siz <b>{tariff}</b> tarifiga yozildingiz 🎉"
GROUP_LINK = (
    "👥 Sizning guruhingiz: <b>{group}</b>\n\n"
    "Pastdagi tugmani bosib qo'shilish so'rovini yuboring — bot uni avtomatik tasdiqlaydi.\n"
    "⚠️ Havola 24 soat amal qiladi va faqat siz uchun."
)
GROUP_WAIT = "⏳ Guruhingiz tayyorlanmoqda. Tez orada sizga guruh havolasi yuboriladi."
ALREADY_IN_GROUP = "Siz allaqachon guruhdasiz ✅"
REJECTED_USER = (
    "❌ <b>To'lovingiz tasdiqlanmadi.</b>\n\n"
    "Sabab: <b>{reason}</b>\n\n"
    "Savollar bo'lsa, «✉️ Admin bilan bog'lanish» orqali yozing. Chekni qaytadan yuborishingiz mumkin."
)

# ============================================================
# OBUNA NAZORATI
# ============================================================
SUB_REMIND_3 = (
    "⏰ Pullik kanal obunangiz tugashiga <b>3 kun</b> qoldi ({end}).\n"
    "Kanalda qolish uchun obunani uzaytiring 👇"
)
SUB_REMIND_1 = (
    "⚠️ Pullik kanal obunangiz tugashiga <b>1 kun</b> qoldi ({end}).\n"
    "Uzaytirmasangiz, kanaldan avtomatik chiqarilasiz 👇"
)
SUB_EXPIRED = (
    "😔 Pullik kanal obunangiz muddati tugadi va siz kanaldan chiqarildingiz.\n"
    "Qaytib kelish uchun obunani uzaytiring 👇"
)
SUB_CANCELLED_USER = "Pullik kanal obunangiz admin tomonidan bekor qilindi."
SUB_EXTENDED_USER = "🎁 Admin obunangizni uzaytirdi. Yangi tugash sanasi: <b>{end}</b>"

DAILY_REPORT = (
    "📊 <b>Kunlik hisobot</b> ({date})\n\n"
    "👥 Yangi lidlar (24 soat): <b>{new_users}</b>\n"
    "   shundan ro'yxatni yakunlaganlar: <b>{new_registered}</b>\n"
    "✅ Tasdiqlangan to'lovlar: <b>{approved}</b> ta — <b>{approved_sum} so'm</b>\n"
    "⏳ Kutilayotgan to'lovlar: <b>{pending}</b>\n"
    "🚪 Kanaldan chiqarilganlar: <b>{expired}</b>\n"
    "⏰ Eslatma yuborilganlar: 3 kun — <b>{reminded3}</b>, 1 kun — <b>{reminded1}</b>\n"
    "💎 Faol pullik obunachilar: <b>{active}</b>"
)

# ============================================================
# ADMIN
# ============================================================
USER_CARD = (
    "👤 {name}\n"
    "📱 {phone}\n"
    "🔗 {username}\n"
    "🆔 <code>{tg_id}</code>\n"
    "🏷 Segment: {segment}\n"
    "📍 Manba: {source}"
)
PAYMENT_CAPTION = (
    "🧾 <b>To'lov #{id}</b>\n\n"
    "{user}\n\n"
    "📦 Mahsulot: <b>{product}</b>\n"
    "💰 Summa: <b>{amount} so'm</b>\n"
    "🕒 {date}"
)
STATUS_APPROVED_BY = "\n\n✅ <b>TASDIQLANDI</b> — {admin} ({date})"
STATUS_REJECTED_BY = "\n\n❌ <b>RAD ETILDI</b> — {admin} ({date})\nSabab: {reason}"
PAYMENT_APPROVED_OK = "✅ Tasdiqlandi"
PAYMENT_REJECTED_OK = "❌ Rad etildi"
PAYMENT_ALREADY_DECIDED = "Bu to'lov allaqachon ko'rib chiqilgan: {status}"
PAYMENT_NOT_FOUND = "To'lov topilmadi."
ASK_REJECT_REASON = "To'lov #{id} uchun rad etish sababini yozing:"
CHOOSE_REJECT_REASON = "Sababni tanlang:"
ADMIN_NO_GROUP = (
    "⚠️ <b>Guruhda bo'sh joy yo'q!</b>\n"
    "Tarif: <b>{tariff}</b>\n{user}\n\n"
    "Yangi guruh qo'shing (guruh ichida /addgroup yozing). Kutayotganlar avtomatik joylashtiriladi."
)
ADMIN_FULFILL_ERROR = (
    "🚨 To'lov #{id} tasdiqlandi, lekin havola yaratishda xato bo'ldi:\n<code>{error}</code>\n\n"
    "Bot kanal/guruhda admin ekanini va «Foydalanuvchi qo'shish» huquqi borligini tekshiring."
)
ADMIN_SUPPORT_MSG = "✉️ <b>Yangi xabar</b>\n\n{user}"
ADMIN_AGENT_ORDER = "🤖 <b>Yangi AI agent buyurtmasi!</b>\n\n{user}"
ASK_ADMIN_REPLY = "Foydalanuvchiga javobingizni yozing (matn, rasm yoki video):"
ADMIN_REPLY_SENT = "✅ Javob yuborildi."
ADMIN_REPLY_FAILED = "❌ Yuborib bo'lmadi (foydalanuvchi botni bloklagan bo'lishi mumkin)."

ADMIN_PANEL = (
    "⚙️ <b>Admin panel</b>\n\n"
    "Kerakli bo'limni tanlang.\n\n"
    "<b>Buyruqlar:</b>\n"
    "/setgift — bepul sovg'a matnini o'zgartirish\n"
    "/setlesson — «Bepul dars» matnini o'zgartirish\n"
    "/setabout — «Men haqimda» matnini o'zgartirish\n"
    "/settariff — tarif narxi va tavsifini o'zgartirish\n"
    "/setseniorlimit 20 — Senior joylar sonini o'zgartirish\n"
    "/addgroup basic 20 — guruh qo'shish (guruh ichida yozing)\n"
    "/groups — guruhlar ro'yxati\n"
    "/cancel — joriy amalni bekor qilish"
)
BTN_ADM_STATS = "📊 Statistika"
BTN_ADM_EXPORT = "📥 Lidlar (Excel)"
BTN_ADM_BROADCAST = "📣 Xabar tarqatish"
BTN_ADM_PENDING = "⏳ Kutilayotgan to'lovlar"
BTN_ADM_SEARCH = "🔎 Foydalanuvchini qidirish"
BTN_ADM_GROUPS = "👥 Guruhlar"

STATS = (
    "📊 <b>Statistika</b>\n\n"
    "👥 Jami lidlar: <b>{total}</b>\n"
    "✅ Ro'yxatni yakunlaganlar: <b>{registered}</b>\n"
    "🚫 Botni bloklaganlar: <b>{blocked}</b>\n\n"
    "<b>Segmentlar:</b>\n{segments}\n\n"
    "<b>Manbalar:</b>\n{sources}\n\n"
    "<b>To'lovlar (tasdiqlangan):</b>\n{payments}\n"
    "Jami: <b>{pay_count}</b> ta — <b>{pay_sum} so'm</b>\n"
    "⏳ Kutilayotgan: <b>{pending}</b>\n\n"
    "💎 Faol pullik obunachilar: <b>{active_subs}</b>\n"
    "🎓 Senior joylar: <b>{senior_used}/{senior_limit}</b>\n\n"
    "<b>Guruhlar:</b>\n{groups}"
)
NO_DATA = "—"
NO_PENDING = "Kutilayotgan to'lovlar yo'q ✅"
PENDING_LIST = "⏳ <b>Kutilayotgan to'lovlar ({count} ta)</b>\n\nKo'rish uchun tugmani bosing:"
EXPORT_CAPTION = "📥 Lidlar ro'yxati ({count} ta)"

ASK_SEARCH = "Foydalanuvchining telefon raqamini yoki Telegram ID sini yuboring:"
SEARCH_NOT_FOUND = "Hech kim topilmadi. Boshqa raqam yoki ID yuboring, yoki /cancel."
SEARCH_RESULT = (
    "{user}\n"
    "📅 Ro'yxatdan o'tgan: {created}\n\n"
    "💎 Pullik kanal: {sub}\n"
    "🎓 Kurslar: {courses}\n"
    "🛒 Xaridlar: {purchases}"
)
SUB_ACTIVE_TILL = "faol, {end} gacha"
SUB_STATUS_NONE = "yo'q"
SUB_STATUS_OTHER = "{status} ({end})"
BTN_EXT_30 = "➕ 30 kun"
BTN_EXT_7 = "➕ 7 kun"
BTN_SUB_CANCEL = "🚫 Obunani bekor qilish"
BTN_SEND_CH_LINK = "🔗 Kanal havolasini yuborish"
BTN_CONFIRM_CANCEL = "⚠️ Ha, bekor qilinsin"
CONFIRM_SUB_CANCEL = "Rostdan ham bu foydalanuvchining obunasini bekor qilib, kanaldan chiqarasizmi?"
ADMIN_SUB_EXTENDED = "✅ Obuna uzaytirildi: {end} gacha"
ADMIN_SUB_CANCELLED = "✅ Obuna bekor qilindi va foydalanuvchi kanaldan chiqarildi."
ADMIN_LINK_SENT = "✅ Havola yuborildi."
USER_NOT_FOUND = "Foydalanuvchi topilmadi."

BC_CHOOSE_AUDIENCE = "📣 <b>Xabar tarqatish</b>\n\nKimga yuboramiz?"
BC_AUDIENCES = {
    "all": "👥 Hammaga",
    "seg:smm": "🏷 SMM mutaxassislari",
    "seg:biz": "🏷 Biznes egalari",
    "seg:learn": "🏷 O'rganuvchilar",
    "nopurchase": "🛒 Xarid qilmaganlar",
    "paid": "💎 Pullik obunachilar",
}
BC_ASK_CONTENT = "Yuboriladigan xabarni jo'nating (matn, rasm yoki video — izoh bilan bo'lishi mumkin):"
BC_ASK_BUTTON = (
    "Xabarga tugma qo'shasizmi?\n\n"
    "Qo'shish uchun shu formatda yozing:\n<code>Tugma matni | https://havola.uz</code>\n\n"
    "Kerak bo'lmasa «⏭ O'tkazib yuborish»ni bosing."
)
BC_BAD_BUTTON = "Format noto'g'ri. Misol: <code>Batafsil | https://t.me/kanal</code>"
BC_PREVIEW = "👆 Xabar shunday ko'rinadi.\n\nAuditoriya: <b>{audience}</b> — <b>{count}</b> kishi.\nYuboramizmi?"
BC_STARTED = "🚀 Tarqatish boshlandi. Tugagach hisobot yuboraman."
BC_DONE = (
    "✅ <b>Tarqatish yakunlandi</b>\n\n"
    "Yuborildi: <b>{ok}</b>\n"
    "Bloklaganlar: <b>{blocked}</b>\n"
    "Xatolar: <b>{failed}</b>"
)
BC_EMPTY = "Bu auditoriyada hech kim yo'q."

ASK_NEW_TEXT = (
    "Hozirgi matn pastda 👇\n\n"
    "Yangi matnni yuboring (formatlash saqlanadi). Bekor qilish: /cancel"
)
TEXT_SAVED = "✅ Saqlandi."
CHOOSE_TARIFF = "Qaysi tarifni o'zgartiramiz?"
ASK_TARIFF_PRICE = (
    "<b>{title}</b>\nHozirgi narx: <b>{price} so'm</b>\n\n"
    "Yangi narxni faqat raqam bilan yozing (masalan: 300000).\nO'zgartirmaslik uchun «-» yuboring."
)
ASK_TARIFF_DESC = (
    "Hozirgi tavsif:\n\n{desc}\n\n"
    "Yangi tavsifni yuboring. O'zgartirmaslik uchun «-» yuboring."
)
BAD_NUMBER = "Iltimos, faqat raqam yozing (masalan: 300000) yoki «-»."
TARIFF_SAVED = "✅ Tarif yangilandi:\n<b>{title}</b> — {price} so'm\n\n{desc}"
SENIOR_LIMIT_SAVED = "✅ Senior joylar soni: {limit}"
SENIOR_LIMIT_USAGE = "Foydalanish: <code>/setseniorlimit 20</code>"

ADDGROUP_USAGE = (
    "Guruh qo'shish:\n"
    "1) Botni guruhga qo'shing va admin qiling («Foydalanuvchi qo'shish» va «Bloklash» huquqlari bilan).\n"
    "2) Guruh ichida yozing: <code>/addgroup basic 20</code>\n"
    "   (tarif: basic / middle / senior / any, oxirgi raqam — sig'im)\n\n"
    "Yoki shaxsiy chatda: <code>/addgroup -1001234567890 basic 20</code>\n\n"
    "⚠️ Guruhda «anonim admin» rejimi o'chiq bo'lishi kerak."
)
ADDGROUP_BAD_TARIFF = "Tarif noto'g'ri. Variantlar: basic, middle, senior, any."
ADDGROUP_NO_ACCESS = "❌ Bot bu guruhni ko'ra olmayapti. Botni guruhga qo'shganingizni tekshiring."
ADDGROUP_NOT_ADMIN = (
    "❌ Bot guruhda admin emas yoki huquqlari yetarli emas.\n"
    "Kerakli huquqlar: «Foydalanuvchi qo'shish (havola orqali taklif)» va «Foydalanuvchilarni bloklash»."
)
ADDGROUP_OK = (
    "✅ Guruh saqlandi: <b>{title}</b>\n"
    "Tarif: {tariff}, sig'im: {capacity}, hozirgi a'zolar: {members}\n"
    "Kutayotganlardan joylashtirildi: {assigned}"
)
GROUPS_EMPTY = "Hali guruh qo'shilmagan.\n\n"
GROUP_LINE = "{icon} <b>{title}</b> — {tariff}, {members}/{capacity}"
GROUPS_HINT = "\n\nTugma bosilsa guruh yoqiladi/o'chiriladi."

STARTUP_CHECK_FAIL = "⚠️ <b>Diqqat!</b> Bot «{chat}» da admin emas yoki huquqlari yetarli emas: {detail}"
STARTUP_NOT_CONFIGURED = "⚠️ {chat} hali kiritilmagan. Web-panel → ⚙️ Sozlamalar bo'limida kiriting."
CHAT_ID_INFO = (
    "📢 <b>{title}</b>\n"
    "ID: <code>{chat_id}</code>\n\n"
    "Shu ID ni nusxalab, web-panel → ⚙️ Sozlamalar bo'limiga qo'ying."
)
BOT_ADDED_TO_CHAT = (
    "✅ Bot <b>{title}</b> ga admin qilindi.\n"
    "Turi: {kind}\nID: <code>{chat_id}</code>\n\n"
    "Kerak bo'lsa, bu ID ni web-panel → ⚙️ Sozlamalar ga qo'ying "
    "(kurs guruhi bo'lsa — guruh ichida /addgroup yozing)."
)
BOT_REMOVED_FROM_CHAT = "⚠️ Bot <b>{title}</b> da adminlikdan olindi yoki chiqarildi (ID: <code>{chat_id}</code>)."
CHAT_KINDS = {"channel": "kanal", "group": "guruh", "supergroup": "guruh"}
ERROR_ALERT ="🚨 <b>Botda xato</b>\n\n<code>{error}</code>"
