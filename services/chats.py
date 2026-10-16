"""Kanal/guruh bilan ishlash: a'zolikni tekshirish, havola yaratish, chiqarish."""
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import InviteLink, User
from services.common import now_utc

log = logging.getLogger(__name__)

LINK_TTL = timedelta(hours=24)
MEMBER_STATUSES = {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}


async def is_member(bot: Bot, chat_id: int | str, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
    except Exception as e:
        log.error("get_chat_member(%s, %s) xatosi: %s", chat_id, user_id, e)
        return False
    if member.status in MEMBER_STATUSES:
        return True
    return member.status == ChatMemberStatus.RESTRICTED and getattr(member, "is_member", False)


async def bot_rights_problem(bot: Bot, chat_id: int | str) -> str | None:
    """Bot chatda kerakli huquqlarga ega bo'lmasa, muammo matnini qaytaradi."""
    try:
        me = await bot.get_chat_member(chat_id, bot.id)
    except Exception as e:
        return f"chatga kirish imkoni yo'q ({e})"
    if me.status != ChatMemberStatus.ADMINISTRATOR:
        return "bot admin emas"
    missing = [
        name for name, attr in (("a'zo qo'shish", "can_invite_users"), ("bloklash", "can_restrict_members"))
        if not getattr(me, attr, False)
    ]
    return ("yetishmayotgan huquqlar: " + ", ".join(missing)) if missing else None


async def create_join_link(
    bot: Bot,
    session: AsyncSession,
    user: User,
    chat_id: int,
    kind: str,
    enrollment_id: int | None = None,
) -> str:
    """Faqat shu foydalanuvchi uchun 24 soatlik join-request havola yaratadi.

    Oldingi ishlatilmagan havolalari bekor qilinadi.
    """
    old = await session.scalars(
        select(InviteLink).where(
            InviteLink.user_id == user.id,
            InviteLink.chat_id == chat_id,
            InviteLink.used.is_(False),
            InviteLink.revoked.is_(False),
        )
    )
    for link in old:
        await revoke_link(bot, link)

    expire_at = now_utc() + LINK_TTL
    invite = await bot.create_chat_invite_link(
        chat_id=chat_id,
        name=f"u{user.tg_id}"[:32],
        expire_date=_ts(expire_at),
        creates_join_request=True,
    )
    session.add(
        InviteLink(
            user_id=user.id,
            chat_id=chat_id,
            link=invite.invite_link,
            kind=kind,
            enrollment_id=enrollment_id,
            expire_at=expire_at,
        )
    )
    await session.commit()
    return invite.invite_link


def _ts(naive_utc: datetime) -> int:
    return int(naive_utc.replace(tzinfo=timezone.utc).timestamp())


async def revoke_link(bot: Bot, link: InviteLink) -> None:
    try:
        await bot.revoke_chat_invite_link(link.chat_id, link.link)
    except Exception as e:
        log.warning("Havolani bekor qilib bo'lmadi (%s): %s", link.link, e)
    link.revoked = True


async def kick_from_chat(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Chiqarish: ban, so'ng darhol unban (keyin qayta qo'shila olishi uchun)."""
    try:
        await bot.ban_chat_member(chat_id, user_id)
        await bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
        return True
    except Exception as e:
        log.error("Foydalanuvchi %s ni %s dan chiqarib bo'lmadi: %s", user_id, chat_id, e)
        return False
