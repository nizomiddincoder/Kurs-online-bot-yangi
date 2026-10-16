"""Admin bilan bog'lanish, AI agent buyurtmasi va admin javobi."""
from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

import texts
from config import Config
from db.repo import get_user
from filters import IsAdmin
from handlers.common import menu_for, registered_user
from keyboards.inline import reply_to_user_kb
from keyboards.reply import cancel_kb
from services.chat import extract, save_incoming, save_outgoing
from services.common import esc, safe_send, user_card

router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE)


class Support(StatesGroup):
    message = State()
    agent = State()
    admin_reply = State()


@router.message(F.text == texts.BTN_CONTACT)
async def contact(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    if await registered_user(message, session):
        await state.set_state(Support.message)
        await message.answer(texts.ASK_SUPPORT_MESSAGE, reply_markup=cancel_kb())


@router.message(F.text == texts.BTN_AI_AGENT)
async def ai_agent(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    user = await registered_user(message, session)
    if user and user.segment == "biz":
        await state.set_state(Support.agent)
        await message.answer(texts.ASK_AGENT_ORDER, reply_markup=cancel_kb())


async def _forward_to_admins(bot: Bot, config: Config, message: Message, header: str) -> None:
    for admin_id in config.admin_ids:
        if await safe_send(bot, admin_id, header, reply_markup=reply_to_user_kb(message.from_user.id)):
            try:
                await message.copy_to(admin_id)
            except Exception:
                pass


@router.message(Support.message)
async def support_message(message: Message, state: FSMContext, session: AsyncSession, bot: Bot, config: Config):
    user = await registered_user(message, session)
    if not user:
        return
    await state.clear()
    await save_incoming(session, user, message)
    await _forward_to_admins(bot, config, message, texts.ADMIN_SUPPORT_MSG.format(user=user_card(user)))
    await message.answer(texts.SUPPORT_SENT, reply_markup=menu_for(user, config, user.tg_id))


@router.message(Support.agent, F.text)
async def agent_order(message: Message, state: FSMContext, session: AsyncSession, bot: Bot, config: Config):
    user = await registered_user(message, session)
    if not user:
        return
    await state.clear()
    await save_incoming(session, user, message, prefix=texts.CHAT_AGENT_PREFIX)
    header = texts.ADMIN_AGENT_ORDER.format(user=user_card(user)) + f"\n\n📝 {esc(message.text)}"
    for admin_id in config.admin_ids:
        await safe_send(bot, admin_id, header, reply_markup=reply_to_user_kb(user.tg_id))
    await message.answer(texts.AGENT_ORDER_SENT, reply_markup=menu_for(user, config, user.tg_id))


@router.message(Support.agent)
async def agent_not_text(message: Message):
    await message.answer(texts.ONLY_TEXT)


# ---------------- Admin javobi ----------------
@router.callback_query(F.data.startswith("rp:"), IsAdmin())
async def admin_reply_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(Support.admin_reply)
    await state.update_data(reply_to=int(cb.data.split(":", 1)[1]))
    await cb.message.answer(texts.ASK_ADMIN_REPLY, reply_markup=cancel_kb())
    await cb.answer()


@router.message(Support.admin_reply, IsAdmin())
async def admin_reply_send(message: Message, state: FSMContext, bot: Bot, session: AsyncSession, config: Config):
    target = (await state.get_data()).get("reply_to")
    await state.clear()
    admin_user = await get_user(session, message.from_user.id)
    kb = menu_for(admin_user, config, message.from_user.id)
    try:
        await bot.send_message(target, texts.ADMIN_REPLY_HEADER)
        await message.copy_to(target)
        await message.answer(texts.ADMIN_REPLY_SENT, reply_markup=kb)
    except Exception:
        await message.answer(texts.ADMIN_REPLY_FAILED, reply_markup=kb)
        return
    target_user = await get_user(session, target)
    if target_user:
        text, media_type, file_id, file_name = extract(message)
        await save_outgoing(session, target_user, text, message.from_user.full_name, media_type, file_id, file_name)
