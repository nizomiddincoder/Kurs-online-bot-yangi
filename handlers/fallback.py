"""Menyudan tashqari yozilgan xabarlar — web-panel chatiga tushadi (eng oxirgi router)."""
from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

import texts
from config import Config
from db.repo import get_user
from handlers.common import menu_for
from handlers.start import _ask_subscribe
from services.chat import recently_wrote, save_incoming

router = Router()


@router.message(F.chat.type == ChatType.PRIVATE, StateFilter(None))
async def fallback(message: Message, state: FSMContext, session: AsyncSession, bot: Bot, config: Config):
    user = await get_user(session, message.from_user.id)
    if user and not user.registered and user.segment and not user.problem and message.text \
            and not message.text.startswith("/"):
        # Bot qayta ishga tushib, «muammo» savoli holati yo'qolgan — javobni shu yerda qabul qilamiz
        user.problem = message.text.strip()[:1000]
        await session.commit()
        await _ask_subscribe(message, state, session, bot, config, user)
        return
    if user is None or not user.registered:
        await message.answer(texts.NEED_START)
        return
    if message.from_user.id in config.admin_ids or (message.text or "").startswith("/"):
        await message.answer(texts.MENU_HINT, reply_markup=menu_for(user, config, message.from_user.id))
        return

    await save_incoming(session, user, message)
    if not await recently_wrote(session, user):
        await message.answer(texts.CHAT_RECEIVED, reply_markup=menu_for(user, config, message.from_user.id))
