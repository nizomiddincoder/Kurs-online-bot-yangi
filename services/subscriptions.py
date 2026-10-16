"""Pullik kanal obunasi."""
from datetime import timedelta

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

import texts
from config import Config
from db.models import Subscription, User
from db.repo import get_subscription
from keyboards.inline import url_kb
from services.chats import create_join_link, is_member, kick_from_chat
from services.common import fmt_date, now_utc, safe_send


async def extend_subscription(session: AsyncSession, user: User, days: int) -> Subscription:
    """Faol obuna bo'lsa — eski tugash sanasiga qo'shadi, bo'lmasa bugundan boshlaydi."""
    now = now_utc()
    sub = await get_subscription(session, user.id)
    if sub is None:
        sub = Subscription(user_id=user.id, start_at=now, end_at=now + timedelta(days=days), status="active")
        session.add(sub)
    elif sub.status == "active" and sub.end_at > now:
        sub.end_at = sub.end_at + timedelta(days=days)
    else:
        sub.start_at = now
        sub.end_at = now + timedelta(days=days)
        sub.status = "active"
        sub.expired_at = None
    sub.reminded_3 = False
    sub.reminded_1 = False
    await session.commit()
    return sub


async def send_channel_link(bot: Bot, session: AsyncSession, config: Config, user: User, text: str) -> None:
    link = await create_join_link(bot, session, user, config.paid_channel_id, kind="channel")
    await safe_send(bot, user.tg_id, text, reply_markup=url_kb(texts.BTN_JOIN_CHANNEL, link))


async def deliver_channel_access(
    bot: Bot, session: AsyncSession, config: Config, user: User, sub: Subscription, by_admin: bool = False
) -> None:
    """Obuna tasdiqlangach: kanalda bo'lsa xabar beradi, bo'lmasa havola yuboradi."""
    end = fmt_date(sub.end_at)
    if await is_member(bot, config.paid_channel_id, user.tg_id):
        text = texts.SUB_EXTENDED_USER if by_admin else texts.PAID_EXTENDED
        await safe_send(bot, user.tg_id, text.format(end=end))
    else:
        await send_channel_link(bot, session, config, user, texts.PAID_APPROVED.format(end=end))


async def cancel_subscription(bot: Bot, session: AsyncSession, config: Config, user: User) -> None:
    sub = await get_subscription(session, user.id)
    if sub and sub.status == "active":
        sub.status = "cancelled"
        sub.expired_at = now_utc()
        await session.commit()
    if await kick_from_chat(bot, config.paid_channel_id, user.tg_id):
        user.paid_member = False
        await session.commit()
    await safe_send(bot, user.tg_id, texts.SUB_CANCELLED_USER)
