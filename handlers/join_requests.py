"""Kanal/guruhga qo'shilish so'rovlari: faqat tasdiqlangan foydalanuvchi qabul qilinadi."""
import logging

from aiogram import Bot, Router
from aiogram.types import ChatJoinRequest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from db.models import Enrollment, Group, InviteLink
from db.repo import get_active_subscription, get_user
from services.chats import revoke_link
from services.common import now_utc

log = logging.getLogger(__name__)
router = Router()


@router.chat_join_request()
async def on_join_request(req: ChatJoinRequest, bot: Bot, session: AsyncSession, config: Config):
    chat_id = req.chat.id
    is_paid_channel = chat_id == config.paid_channel_id
    group = None if is_paid_channel else await session.scalar(select(Group).where(Group.chat_id == chat_id))
    if not is_paid_channel and group is None:
        return  # bizga tegishli bo'lmagan chat — tegmaymiz

    user = await get_user(session, req.from_user.id)
    link = None
    approve = False
    enrollment = None

    if user:
        links = list(await session.scalars(
            select(InviteLink).where(
                InviteLink.user_id == user.id,
                InviteLink.chat_id == chat_id,
                InviteLink.used.is_(False),
                InviteLink.revoked.is_(False),
                InviteLink.expire_at > now_utc(),
            ).order_by(InviteLink.id.desc())
        ))
        requested = req.invite_link.invite_link if req.invite_link else None
        link = next((ln for ln in links if ln.link == requested), links[0] if links else None)

        if link and is_paid_channel and link.kind == "channel":
            approve = await get_active_subscription(session, user.id) is not None
        elif link and group and link.kind == "group" and link.enrollment_id:
            enrollment = await session.get(Enrollment, link.enrollment_id)
            approve = enrollment is not None and enrollment.user_id == user.id and enrollment.group_id == group.id

    try:
        if approve:
            await req.approve()
            link.used = True
            await revoke_link(bot, link)  # bir martalik: darhol bekor qilinadi
            if enrollment:
                enrollment.status = "joined"
                enrollment.joined_at = now_utc()
            else:
                user.paid_member = True
                user.members_checked_at = now_utc()
            await session.commit()
            log.info("Join request qabul qilindi: user=%s chat=%s", req.from_user.id, chat_id)
        else:
            await req.decline()
            log.info("Join request rad etildi: user=%s chat=%s", req.from_user.id, chat_id)
    except Exception:
        log.exception("Join request xatosi (user=%s chat=%s)", req.from_user.id, chat_id)
