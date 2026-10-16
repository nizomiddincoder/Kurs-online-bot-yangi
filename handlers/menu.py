"""Asosiy menyu: Online kurs | Pullik kanal | Bepul dars | Men haqimda."""
from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from sqlalchemy.ext.asyncio import AsyncSession

import texts
from config import Config
from db.models import Enrollment
from db.repo import get_active_subscription, get_user, user_enrollments
from handlers.common import registered_user
from keyboards.inline import pay_kb, tariffs_kb
from services.chats import is_member
from services.common import esc, fmt_date, fmt_money
from services.courses import resend_group_link
from services.settings import get_tariff, get_text, senior_is_full
from services.subscriptions import send_channel_link

router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE)

TARIFFS = ("basic", "middle", "senior")


# ---------------- Online kurs ----------------
async def _course_view(session: AsyncSession, config: Config, user) -> tuple[str, object]:
    tariffs = [await get_tariff(session, config, t) for t in TARIFFS]
    full = await senior_is_full(session, config)
    text = texts.COURSE_INTRO
    for t in tariffs:
        mark = f" — <b>{texts.SEATS_FULL}</b>" if t["code"] == "senior" and full else ""
        text += texts.COURSE_TARIFF_LINE.format(title=t["title"], price=fmt_money(t["price"]), full=mark)
    extra = [
        InlineKeyboardButton(text=f"{texts.BTN_GET_GROUP_LINK} ({texts.TARIFF_NAMES[e.tariff]})", callback_data=f"grplink:{e.id}")
        for e in await user_enrollments(session, user.id) if e.group_id
    ]
    return text, tariffs_kb(tariffs, full, extra)


@router.message(F.text == texts.BTN_COURSE)
async def course_menu(message: Message, state: FSMContext, session: AsyncSession, config: Config):
    await state.clear()
    user = await registered_user(message, session)
    if not user:
        return
    text, kb = await _course_view(session, config, user)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "course:list")
async def course_back(cb: CallbackQuery, session: AsyncSession, config: Config):
    user = await get_user(session, cb.from_user.id)
    text, kb = await _course_view(session, config, user)
    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.startswith("tariff:"))
async def tariff_detail(cb: CallbackQuery, session: AsyncSession, config: Config):
    code = cb.data.split(":", 1)[1]
    if code not in TARIFFS:
        await cb.answer()
        return
    if code == "senior" and await senior_is_full(session, config):
        await cb.answer(texts.SEATS_FULL_ALERT, show_alert=True)
        return
    t = await get_tariff(session, config, code)
    text = texts.TARIFF_DETAIL.format(
        title=t["title"], desc=t["desc"], price=fmt_money(t["price"]),
        card=esc(config.card_number), holder=esc(config.card_holder),
    )
    await cb.message.edit_text(text, reply_markup=pay_kb(f"tariff_{code}", back="course:list"))
    await cb.answer()


@router.callback_query(F.data.startswith("grplink:"))
async def group_link(cb: CallbackQuery, session: AsyncSession, bot: Bot):
    enr = await session.get(Enrollment, int(cb.data.split(":", 1)[1]))
    if enr is None or enr.user.tg_id != cb.from_user.id:
        await cb.answer()
        return
    result = await resend_group_link(bot, session, enr)
    await cb.answer(result or None, show_alert=bool(result))


# ---------------- Pullik kanal ----------------
@router.message(F.text == texts.BTN_PAID)
async def paid_channel(message: Message, state: FSMContext, session: AsyncSession, config: Config):
    await state.clear()
    user = await registered_user(message, session)
    if not user:
        return
    text = texts.PAID_CHANNEL_INFO.format(
        price=fmt_money(config.paid_channel_price), card=esc(config.card_number), holder=esc(config.card_holder)
    )
    extra = None
    sub = await get_active_subscription(session, user.id)
    if sub:
        text += texts.PAID_CHANNEL_ACTIVE.format(end=fmt_date(sub.end_at))
        extra = [InlineKeyboardButton(text=texts.BTN_GET_CHANNEL_LINK, callback_data="chlink")]
    await message.answer(text, reply_markup=pay_kb("paid_channel", extra=extra))


@router.callback_query(F.data == "chlink")
async def channel_link(cb: CallbackQuery, session: AsyncSession, bot: Bot, config: Config):
    user = await get_user(session, cb.from_user.id)
    if user is None or await get_active_subscription(session, user.id) is None:
        await cb.answer(texts.NO_ACTIVE_SUB, show_alert=True)
        return
    if await is_member(bot, config.paid_channel_id, user.tg_id):
        await cb.answer(texts.ALREADY_IN_CHANNEL, show_alert=True)
        return
    await send_channel_link(bot, session, config, user, texts.CHANNEL_LINK)
    await cb.answer()


# ---------------- Bepul dars / Men haqimda ----------------
@router.message(F.text == texts.BTN_FREE_LESSON)
async def free_lesson(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    if await registered_user(message, session):
        await message.answer(await get_text(session, "lesson_text"), disable_web_page_preview=False)


@router.message(F.text == texts.BTN_ABOUT)
async def about(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    if await registered_user(message, session):
        await message.answer(await get_text(session, "about_text"), disable_web_page_preview=False)
