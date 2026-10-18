"""/start: ism → telefon → segment → bepul kanalga obuna → sovg'a + menyu."""
import re
import time

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

import texts
from config import Config
from db.models import User
from db.repo import get_user
from handlers.common import menu_for
from keyboards.inline import segments_kb, subscribe_kb
from keyboards.reply import phone_kb
from services.chats import check_member, free_channel_link
from services.common import esc, now_utc
from services.notify import notify_admins
from services.settings import get_text

router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE)

SOURCE_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class Reg(StatesGroup):
    name = State()
    phone = State()
    segment = State()
    subscribe = State()


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext, session: AsyncSession, config: Config):
    await state.clear()
    args = (command.args or "").strip()
    source = args if SOURCE_RE.match(args) else None
    tg = message.from_user

    user = await get_user(session, tg.id)
    if user is None:
        user = User(tg_id=tg.id, username=tg.username, source=source or "direct")
        session.add(user)
    else:
        user.username = tg.username
        user.is_blocked = False
    await session.commit()

    if user.registered:
        await message.answer(
            texts.WELCOME_BACK.format(name=esc(user.full_name)),
            reply_markup=menu_for(user, config, tg.id),
        )
        return

    await message.answer(texts.WELCOME, reply_markup=ReplyKeyboardRemove())
    await state.set_state(Reg.name)


@router.message(Reg.name, F.text)
async def got_name(message: Message, state: FSMContext, session: AsyncSession):
    name = " ".join(message.text.split())
    if name.startswith("/") or not (2 <= len(name) <= 100):
        await message.answer(texts.ASK_NAME_AGAIN)
        return
    user = await get_user(session, message.from_user.id)
    if user is None:
        await message.answer(texts.NEED_START)
        return
    user.full_name = name
    await session.commit()
    await message.answer(texts.ASK_PHONE.format(name=esc(name)), reply_markup=phone_kb())
    await state.set_state(Reg.phone)


@router.message(Reg.name)
async def name_not_text(message: Message):
    await message.answer(texts.ASK_NAME_AGAIN)


@router.message(Reg.phone, F.contact)
async def got_phone(message: Message, state: FSMContext, session: AsyncSession):
    if message.contact.user_id != message.from_user.id:
        await message.answer(texts.PHONE_NOT_OWN, reply_markup=phone_kb())
        return
    digits = re.sub(r"\D", "", message.contact.phone_number)
    user = await get_user(session, message.from_user.id)
    if user is None:
        await message.answer(texts.NEED_START)
        return
    user.phone = "+" + digits
    await session.commit()
    await message.answer(texts.PHONE_SAVED, reply_markup=ReplyKeyboardRemove())
    await message.answer(texts.ASK_SEGMENT, reply_markup=segments_kb())
    await state.set_state(Reg.segment)


@router.message(Reg.phone)
async def phone_not_contact(message: Message):
    await message.answer(texts.PHONE_USE_BUTTON, reply_markup=phone_kb())


@router.message(Reg.segment)
@router.message(Reg.subscribe)
async def press_buttons(message: Message):
    await message.answer(texts.USE_BUTTONS)


# Callback'lar holatga bog'lanmagan: bot qayta ishga tushsa ham ishlaydi
@router.callback_query(F.data.startswith("seg:"))
async def got_segment(cb: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot, config: Config):
    code = cb.data.split(":", 1)[1]
    user = await get_user(session, cb.from_user.id)
    if code not in texts.SEGMENTS or user is None or not user.phone:
        await cb.answer(texts.NEED_START, show_alert=True)
        return
    user.segment = code
    await session.commit()
    try:
        await cb.message.edit_text(texts.SEGMENT_CHOSEN.format(segment=texts.SEGMENTS[code]))
    except TelegramBadRequest:
        # Tugma ikkinchi marta bosilgan — keyingi qadam allaqachon yuborilgan, takrorlamaymiz
        await cb.answer()
        return
    await cb.answer()

    if user.registered:  # segmentni qayta tanlagan bo'lsa
        await cb.message.answer(texts.MENU_HINT, reply_markup=menu_for(user, config, cb.from_user.id))
        return

    if not config.free_channel_id:
        # Bepul kanal hali sozlanmagan — foydalanuvchini kutdirmaymiz, obuna bosqichi o'tkazib yuboriladi
        await _alert_admins_once(bot, config, texts.ADMIN_FREE_CHANNEL_MISSING)
        await _finish_registration(cb.message, session, user, config, subscribed=False)
        await state.clear()
        return

    link = await free_channel_link(bot, config)
    if not link:
        await _alert_admins_once(bot, config, texts.ADMIN_FREE_LINK_MISSING)
    await cb.message.answer(texts.ASK_SUBSCRIBE, reply_markup=subscribe_kb(link))
    await state.set_state(Reg.subscribe)


_last_alert: dict[str, float] = {}


async def _alert_admins_once(bot: Bot, config: Config, text: str) -> None:
    """Sozlama muammosi haqida adminga soatiga ko'pi bilan bir marta yozadi."""
    if time.monotonic() - _last_alert.get(text, -1e9) > 3600:
        _last_alert[text] = time.monotonic()
        await notify_admins(bot, config, text)


async def _finish_registration(message: Message, session: AsyncSession, user: User, config: Config,
                               subscribed: bool) -> None:
    if not user.registered:
        user.registered = True
        user.registered_at = now_utc()
        await session.commit()
        await message.answer(texts.SUB_CONFIRMED if subscribed else texts.REG_DONE)
        await message.answer(await get_text(session, "gift_text"), disable_web_page_preview=True)
    await message.answer(texts.MENU_HINT, reply_markup=menu_for(user, config, user.tg_id))


@router.callback_query(F.data == "sub:check")
async def check_subscription(cb: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot, config: Config):
    user = await get_user(session, cb.from_user.id)
    if user is None or not user.segment:
        await cb.answer(texts.NEED_START, show_alert=True)
        return
    member = await check_member(bot, config.free_channel_id, cb.from_user.id)
    if member is False:
        await cb.answer(texts.NOT_SUBSCRIBED, show_alert=True)
        return
    if member is None:
        # Bot kanalni tekshira olmadi (bot admin emas / kanal ID xato) — foydalanuvchi aybdor emas, o'tkazamiz
        await _alert_admins_once(bot, config, texts.ADMIN_FREE_CHECK_FAILED)

    await cb.answer()
    await state.clear()
    if member:
        user.free_member = True
        user.members_checked_at = now_utc()
        await session.commit()
    try:
        await cb.message.delete()
    except Exception:
        if user.registered:
            return  # «Tekshirish» ikkinchi marta bosilgan — sovg'a va menyu allaqachon yuborilgan

    await _finish_registration(cb.message, session, user, config, subscribed=bool(member))
