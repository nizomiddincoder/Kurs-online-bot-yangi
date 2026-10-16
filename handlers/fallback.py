"""Menyudan tashqari yozilgan xabarlar — web-panel chatiga tushadi (eng oxirgi router)."""
from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import StateFilter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

import texts
from config import Config
from db.repo import get_user
from handlers.common import menu_for
from services.chat import recently_wrote, save_incoming

router = Router()


@router.message(F.chat.type == ChatType.PRIVATE, StateFilter(None))
async def fallback(message: Message, session: AsyncSession, config: Config):
    user = await get_user(session, message.from_user.id)
    if user is None or not user.registered:
        await message.answer(texts.NEED_START)
        return
    if message.from_user.id in config.admin_ids or (message.text or "").startswith("/"):
        await message.answer(texts.MENU_HINT, reply_markup=menu_for(user, config, message.from_user.id))
        return

    await save_incoming(session, user, message)
    if not await recently_wrote(session, user):
        await message.answer(texts.CHAT_RECEIVED, reply_markup=menu_for(user, config, message.from_user.id))
