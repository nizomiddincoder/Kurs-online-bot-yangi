"""Kanal/guruh ID sini oson bilish:
- admin kanaldan postni botga forward qilsa — bot ID ni yozib beradi;
- bot biror kanal/guruhga admin qilinsa — adminlarga ID bilan xabar keladi.
"""
from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import StateFilter
from aiogram.types import ChatMemberUpdated, Message

import texts
from config import Config
from filters import IsAdmin
from services.common import esc
from services.notify import notify_admins

router = Router()


@router.message(F.chat.type == ChatType.PRIVATE, F.forward_origin, IsAdmin(), StateFilter(None))
async def forwarded_from_chat(message: Message):
    origin = message.forward_origin
    chat = getattr(origin, "chat", None) or getattr(origin, "sender_chat", None)
    if chat is None:
        await message.answer("Bu xabar kanal yoki guruhdan emas. Kanal postini forward qiling.")
        return
    await message.answer(texts.CHAT_ID_INFO.format(title=esc(chat.title), chat_id=chat.id))


@router.my_chat_member(F.chat.type.in_({ChatType.CHANNEL, ChatType.GROUP, ChatType.SUPERGROUP}))
async def bot_rights_changed(update: ChatMemberUpdated, bot: Bot, config: Config):
    old, new = update.old_chat_member.status, update.new_chat_member.status
    chat = update.chat
    if new == ChatMemberStatus.ADMINISTRATOR and old != ChatMemberStatus.ADMINISTRATOR:
        await notify_admins(bot, config, texts.BOT_ADDED_TO_CHAT.format(
            title=esc(chat.title), kind=texts.CHAT_KINDS.get(chat.type, chat.type), chat_id=chat.id,
        ))
    elif old == ChatMemberStatus.ADMINISTRATOR and new != ChatMemberStatus.ADMINISTRATOR:
        await notify_admins(bot, config, texts.BOT_REMOVED_FROM_CHAT.format(title=esc(chat.title), chat_id=chat.id))
