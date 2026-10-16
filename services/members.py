"""Foydalanuvchi bepul va pullik kanalda bormi — tekshirish."""
import asyncio
import logging

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from config import Config
from db.models import User
from services.chats import is_member
from services.common import now_utc

log = logging.getLogger(__name__)

progress = {"running": False, "done": 0, "total": 0}
_task: asyncio.Task | None = None


async def refresh_user(bot: Bot, session: AsyncSession, config: Config, user: User) -> None:
    user.free_member = await is_member(bot, config.free_channel_id, user.tg_id)
    user.paid_member = await is_member(bot, config.paid_channel_id, user.tg_id)
    user.members_checked_at = now_utc()
    await session.commit()


async def _refresh_all(bot: Bot, sessionmaker: async_sessionmaker, config: Config) -> None:
    try:
        async with sessionmaker() as session:
            users = list(await session.scalars(select(User).where(User.registered.is_(True))))
            progress.update(running=True, done=0, total=len(users))
            for user in users:
                try:
                    await refresh_user(bot, session, config, user)
                except Exception as e:
                    log.warning("A'zolikni tekshirib bo'lmadi (%s): %s", user.tg_id, e)
                progress["done"] += 1
                await asyncio.sleep(0.1)  # 2 so'rov / 0.1 s = 20 so'rov/s
    finally:
        progress["running"] = False


def start_refresh_all(bot: Bot, sessionmaker: async_sessionmaker, config: Config) -> bool:
    global _task
    if progress["running"]:
        return False
    progress.update(running=True, done=0, total=0)
    _task = asyncio.create_task(_refresh_all(bot, sessionmaker, config))
    return True
