"""Webinar voronkasi: shaxsiy taklif, dars eslatmalari, follow-up va downsell.

Qanday ishlaydi: har daqiqada (TEST_MODE'da har 5 soniyada) funnel_tick bazaga qaraydi —
«hozir kimga qaysi xabar ketishi kerak va hali ketmagan?». Har bir yuborilgan xabar funnel_marks
jadvalida belgilanadi, shuning uchun restartdan keyin ham hech narsa yo'qolmaydi va takrorlanmaydi.
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.types import InlineKeyboardButton as Btn
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy import and_, exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import texts
from config import Config
from db.models import Enrollment, FunnelMark, Payment, User
from db.repo import get_active_subscription
from services import common
from services.broadcast import _deliver
from services.chats import create_join_link, free_channel_link, is_member
from services.notify import notify_admins
from services.settings import get_setting, get_tariff, get_text
from services.subscriptions import extend_subscription

log = logging.getLogger(__name__)

COURSE_PRODUCTS = ("tariff_standard", "tariff_premium")
SEND_DELAY = 0.05  # 20 xabar/soniya — Telegram limitidan past
BATCH = 300  # bir tikda bitta bosqich uchun ko'pi bilan shuncha odam (qolgani keyingi tikda)
RECORDING_HOURS = 24
MONTHS = ("yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr",
          "noyabr", "dekabr")


# ---------------- Vaqt ----------------
def hours(config: Config, n: float) -> timedelta:
    """TEST_MODE: soat → daqiqa."""
    return timedelta(minutes=n) if config.test_mode else timedelta(hours=n)


def minutes(config: Config, n: float) -> timedelta:
    """TEST_MODE: daqiqa → soniya."""
    return timedelta(seconds=n) if config.test_mode else timedelta(minutes=n)


def fmt_left(delta: timedelta) -> str:
    secs = max(0, int(delta.total_seconds()))
    days, rem = divmod(secs, 86400)
    hrs, rem = divmod(rem, 3600)
    mins, sec = divmod(rem, 60)
    if not (days or hrs or mins):
        return f"{sec} soniya"
    parts = []
    if days:
        parts.append(f"{days} kun")
    if hrs:
        parts.append(f"{hrs} soat")
    if mins and not days:
        parts.append(f"{mins} daqiqa")
    return " ".join(parts)


def fmt_when(dt: datetime | None) -> str:
    if not dt:
        return "—"
    local = common.to_local(dt)
    return f"{local.day}-{MONTHS[local.month - 1]}, soat {local:%H:%M}"


def webinar_line(config: Config) -> str:
    return texts.WEBINAR_LINE.format(when=fmt_when(config.webinar_at)) if config.webinar_at else ""


# ---------------- Taklif ----------------
def offer_active(user: User, now: datetime | None = None) -> bool:
    now = now or common.now_utc()
    return bool(user.offer_expires_at and user.offer_expires_at > now)


async def start_offer(session: AsyncSession, config: Config, user: User, now: datetime | None = None) -> bool:
    """Shaxsiy taklif taymerini boshlaydi (faqat bir marta). True — hozir boshlandi."""
    if user.offer_started_at:
        return False
    now = now or common.now_utc()
    user.offer_started_at = now
    user.offer_expires_at = now + hours(config, config.offer_hours)
    await session.commit()
    return True


async def premium_left(session: AsyncSession, config: Config) -> int:
    sold = await session.scalar(
        select(func.count()).select_from(Payment).where(
            Payment.product == "tariff_premium", Payment.status == "approved"
        )
    ) or 0
    return max(0, config.premium_seats - sold)


async def offer_view(session: AsyncSession, config: Config, user: User,
                     now: datetime | None = None) -> tuple[str, InlineKeyboardMarkup]:
    """Ikki tarif: taklif muddati ichida <s>to'liq</s> → maxsus narx, keyin to'liq narx."""
    now = now or common.now_utc()
    active = offer_active(user, now)
    parts = [texts.OFFER_HEAD.format(left=fmt_left(user.offer_expires_at - now)) if active else texts.OFFER_HEAD_FULL]
    rows = []
    seats = await premium_left(session, config)
    for code, icon in (("standard", "📗"), ("premium", "👑")):
        t = await get_tariff(session, config, code)
        special = active and t["offer"] < t["price"]
        pay = t["offer"] if special else t["price"]
        price = (texts.OFFER_PRICE_SPECIAL.format(full=common.fmt_money(t["price"]), offer=common.fmt_money(t["offer"]))
                 if special else texts.OFFER_PRICE_FULL.format(full=common.fmt_money(t["price"])))
        extra = ""
        if code == "premium":
            extra = (texts.OFFER_SEATS.format(left=seats, total=config.premium_seats) if seats > 0
                     else texts.OFFER_SEATS_GONE)
        parts.append(texts.OFFER_TARIFF.format(icon=icon, title=t["title"], price=price, extra=extra, desc=t["desc"]))
        if code == "premium" and seats <= 0:
            rows.append([Btn(text=texts.BTN_PREMIUM_GONE, callback_data="premium:gone")])
        else:
            rows.append([Btn(text=texts.BTN_TARIFF_PRICE.format(title=t["title"], price=common.fmt_money(pay)),
                             callback_data=f"pay:tariff_{code}")])
    return "".join(parts) + texts.OFFER_FOOT, InlineKeyboardMarkup(inline_keyboard=rows)


async def send_bonus(bot: Bot, session: AsyncSession, chat_id: int) -> None:
    await common.safe_send(bot, chat_id, await get_text(session, "bonus_text"))
    raw = await get_setting(session, "bonus_file")
    if not raw:
        return
    media = json.loads(raw)
    send = {"photo": bot.send_photo, "video": bot.send_video}.get(media["type"], bot.send_document)
    try:
        await send(chat_id, media["file_id"], caption=media.get("caption") or None)
    except Exception as e:
        log.warning("Bonus faylni yuborib bo'lmadi: %s", e)


# ---------------- Kurs to'lovi tasdiqlanganda ----------------
async def deliver_course(bot: Bot, session: AsyncSession, config: Config, user: User, tariff: str,
                         payment_id: int) -> None:
    """Premium → kurs guruhi, Standart → yozuvlar chati; ikkalasiga pullik kanal va obuna +30 kun."""
    sub = await extend_subscription(session, user, config.subscription_days)
    chat_id = config.course_group_id if tariff == "premium" else config.recordings_chat_id
    enrollment = Enrollment(user=user, payment_id=payment_id, tariff=tariff,
                            status="link_sent" if chat_id else "no_chat")
    session.add(enrollment)
    await session.commit()

    rows, later = [], ""
    if chat_id:
        link = await create_join_link(bot, session, user, chat_id, kind="course", enrollment_id=enrollment.id)
        label = texts.BTN_COURSE_GROUP if tariff == "premium" else texts.BTN_RECORDINGS
        rows.append([Btn(text=label, url=link)])
    else:
        later = texts.COURSE_LINK_LATER
        await notify_admins(bot, config, texts.ADMIN_COURSE_CHAT_MISSING.format(
            tariff=texts.TARIFF_NAMES[tariff], what=texts.COURSE_CHAT_NAMES[tariff], user=common.user_card(user),
        ))
    if config.paid_channel_id and not await is_member(bot, config.paid_channel_id, user.tg_id):
        link = await create_join_link(bot, session, user, config.paid_channel_id, kind="channel")
        rows.append([Btn(text=texts.BTN_JOIN_CHANNEL, url=link)])

    text = texts.COURSE_APPROVED_LINKS.format(tariff=texts.TARIFF_NAMES[tariff], end=common.fmt_date(sub.end_at)) + later
    await common.safe_send(bot, user.tg_id, text,
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=rows) if rows else None)


# ---------------- Avtomatik xabarlar (tik) ----------------
def _audience():
    return and_(User.registered.is_(True), User.is_blocked.is_not(True))


def _no_course_payment():
    """To'lamagan: tasdiqlangan yoki tekshirilayotgan kurs to'lovi yo'q."""
    return ~exists().where(
        Payment.user_id == User.id, Payment.product.in_(COURSE_PRODUCTS),
        Payment.status.in_(("approved", "pending")),
    )


def _not_marked(key: str):
    return ~exists().where(FunnelMark.user_id == User.id, FunnelMark.key == key)


async def _mark(session: AsyncSession, user_id: int, key: str) -> bool:
    """Belgilaydi; allaqachon belgilangan bo'lsa False (xabar ikkinchi marta ketmaydi)."""
    session.add(FunnelMark(user_id=user_id, key=key))
    try:
        await session.commit()
        return True
    except IntegrityError:
        await session.rollback()
        return False


async def _send(bot: Bot, session: AsyncSession, user: User, text: str, kb=None) -> bool:
    result = await _deliver(lambda chat_id: bot.send_message(chat_id, text, reply_markup=kb), user.tg_id)
    if result == "blocked":
        user.is_blocked = True
        await session.commit()
    await asyncio.sleep(SEND_DELAY)
    return result == "ok"


def webinar_key(config: Config) -> str:
    return "w" + config.webinar_at.strftime("%Y%m%d%H%M")


def reminder_schedule(config: Config) -> list[tuple[str, datetime]]:
    """Dars vaqtiga nisbatan: -24 soat, dars kuni 10:00, -1 soat, -10 daqiqa."""
    w = config.webinar_at
    if config.test_mode:
        day = w - hours(config, 12)  # test: «dars kuni 10:00» o'rniga 12 daqiqa oldin
    else:
        local = common.to_local(w).replace(hour=10, minute=0, second=0, microsecond=0)
        day = local.astimezone(timezone.utc).replace(tzinfo=None)
    items = [("r24", w - hours(config, 24)), ("rday", day), ("r1h", w - hours(config, 1)),
             ("r10m", w - minutes(config, 10))]
    return sorted((i for i in items if i[1] < w), key=lambda i: i[1])


def _reminder_text(name: str, config: Config, now: datetime) -> str:
    w = config.webinar_at
    template = {"r24": texts.REMIND_24H, "rday": texts.REMIND_DAY, "r1h": texts.REMIND_1H,
                "r10m": texts.REMIND_10M}[name]
    return template.format(when=fmt_when(w), left=fmt_left(w - now), time=f"{common.to_local(w):%H:%M}")


async def _users(session: AsyncSession, *conditions) -> list[User]:
    return list(await session.scalars(select(User).where(_audience(), *conditions).order_by(User.id).limit(BATCH)))


async def _webinar_reminders(bot, session, config, now) -> int:
    w = config.webinar_at
    if not w or now >= w:
        return 0
    due = [item for item in reminder_schedule(config) if item[1] <= now]
    if not due:
        return 0
    name = due[-1][0]  # faqat eng so'nggi eslatma (kech ro'yxatdan o'tganlarga eskisi ketmaydi)
    key = f"{webinar_key(config)}:{name}"
    link = await free_channel_link(bot, config)
    kb = InlineKeyboardMarkup(inline_keyboard=[[Btn(text=texts.BTN_OPEN_CHANNEL, url=link)]]) if link else None
    sent = 0
    for user in await _users(session, _not_marked(key)):
        if await _mark(session, user.id, key):
            sent += await _send(bot, session, user, _reminder_text(name, config, now), kb)
    return sent


async def _after_webinar(bot, session, config, now) -> int:
    """Dars + 2 soat: to'lamaganlarga taklif + «yozuv 24 soat mavjud». Kod so'z yozmaganlarning
    taklif taymeri shu paytdan boshlanadi."""
    w = config.webinar_at
    if not w:
        return 0
    start = w + hours(config, 2)
    if not (start <= now < start + hours(config, RECORDING_HOURS)):
        return 0
    key = f"{webinar_key(config)}:after"
    sent = 0
    for user in await _users(session, _no_course_payment(), _not_marked(key)):
        if await _mark(session, user.id, key):
            await start_offer(session, config, user, now)
            offer_text, kb = await offer_view(session, config, user, now)
            text = texts.FOLLOWUP_AFTER.format(rec_hours=RECORDING_HOURS) + "\n\n" + offer_text
            sent += await _send(bot, session, user, text, kb)
    return sent


async def _offer_followups(bot, session, config, now) -> int:
    show_kb = InlineKeyboardMarkup(inline_keyboard=[[Btn(text=texts.BTN_SHOW_OFFER, callback_data="offer:show")]])
    started = User.offer_started_at.is_not(None)
    sent = 0

    # +24 soat: keys / savol-javob
    for user in await _users(session, _no_course_payment(), started, _not_marked("of24"),
                             User.offer_started_at <= now - hours(config, 24), User.offer_expires_at > now):
        if await _mark(session, user.id, "of24"):
            text = texts.FOLLOWUP_24.format(left=fmt_left(user.offer_expires_at - now))
            sent += await _send(bot, session, user, text, show_kb)

    # Muddat tugashiga 4 soat qolganda (48 soatlik taklifda +44 soat)
    for user in await _users(session, _no_course_payment(), started, _not_marked("of44"),
                             User.offer_expires_at <= now + hours(config, 4), User.offer_expires_at > now):
        if await _mark(session, user.id, "of44"):
            text = texts.FOLLOWUP_44.format(left=fmt_left(user.offer_expires_at - now))
            sent += await _send(bot, session, user, text, show_kb)

    # Muddat tugadi: downsell — pullik kanal (allaqachon obunasi bo'lsa yuborilmaydi)
    downsell_kb = InlineKeyboardMarkup(inline_keyboard=[[Btn(
        text=texts.BTN_DOWNSELL.format(price=common.fmt_money(config.paid_channel_price)),
        callback_data="pay:paid_channel")]])
    for user in await _users(session, _no_course_payment(), started, _not_marked("ofend"),
                             User.offer_expires_at <= now, User.offer_expires_at > now - hours(config, 24 * 7)):
        if await _mark(session, user.id, "ofend") and not await get_active_subscription(session, user.id):
            text = texts.DOWNSELL.format(price=common.fmt_money(config.paid_channel_price))
            sent += await _send(bot, session, user, text, downsell_kb)
    return sent


async def funnel_tick(bot: Bot, sessionmaker: async_sessionmaker, config: Config,
                      now: datetime | None = None) -> int:
    now = now or common.now_utc()
    total = 0
    for step in (_webinar_reminders, _after_webinar, _offer_followups):
        try:
            async with sessionmaker() as session:
                total += await step(bot, session, config, now)
        except Exception:
            log.exception("Voronka bosqichida xato: %s", step.__name__)
    if total:
        log.info("Voronka: %s ta xabar yuborildi", total)
    return total
