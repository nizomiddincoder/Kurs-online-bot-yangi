"""Bekor qilish va yordamchi funksiyalar (boshqa handlerlar ham ishlatadi)."""
from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

import texts
from config import Config
from db.models import User
from db.repo import get_user
from keyboards.reply import main_menu

router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE)


def menu_for(user: User | None, config: Config, tg_id: int):
    return main_menu(user.segment if user else None, tg_id in config.admin_ids)


async def registered_user(message: Message, session: AsyncSession) -> User | None:
    """Ro'yxatdan o'tgan foydalanuvchini qaytaradi, aks holda /start ni so'raydi."""
    user = await get_user(session, message.chat.id)
    if user is None or not user.registered:
        await message.answer(texts.NEED_START)
        return None
    return user


@router.message(F.text == texts.BTN_CANCEL)
@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext, session: AsyncSession, config: Config):
    await state.clear()
    user = await get_user(session, message.from_user.id)
    if user is None or not user.registered:
        await message.answer(texts.NEED_START, reply_markup=ReplyKeyboardRemove())
        return
    await message.answer(texts.CANCELLED, reply_markup=menu_for(user, config, message.from_user.id))
