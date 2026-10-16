"""Xabar tarqatish: sekundiga 20 tadan oshmaydi, bloklaganlar belgilanadi."""
import asyncio
import logging
from typing import Awaitable, Callable

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import texts
from db.models import User
from db.repo import audience_query
from services.common import safe_send

log = logging.getLogger(__name__)

DELAY = 0.05  # 20 xabar/sekund (Telegram limiti 30, xavfsiz zaxira bilan)
_tasks: set[asyncio.Task] = set()


async def count_audience(session: AsyncSession, audience: str) -> int:
    return await session.scalar(select(func.count()).select_from(audience_query(audience).subquery())) or 0


async def _deliver(send: Callable[[int], Awaitable], chat_id: int) -> str:
    for _ in range(3):
        try:
            await send(chat_id)
            return "ok"
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
        except TelegramForbiddenError:
            return "blocked"
        except TelegramBadRequest as e:
            if "chat not found" in str(e).lower() or "deactivated" in str(e).lower():
                return "blocked"
            log.warning("Broadcast %s: %s", chat_id, e)
            return "failed"
        except Exception as e:
            log.warning("Broadcast %s: %s", chat_id, e)
            return "failed"
    return "failed"


async def run_broadcast(
    bot: Bot,
    sessionmaker: async_sessionmaker,
    admin_ids: list[int],
    audience: str,
    send: Callable[[int], Awaitable],
) -> None:
    """send(chat_id) — bitta foydalanuvchiga yuborish funksiyasi."""
    async with sessionmaker() as session:
        ids = list(await session.scalars(audience_query(audience)))

    ok = blocked = failed = 0
    blocked_ids: list[int] = []
    for tg_id in ids:
        result = await _deliver(send, tg_id)
        if result == "ok":
            ok += 1
        elif result == "blocked":
            blocked += 1
            blocked_ids.append(tg_id)
        else:
            failed += 1
        await asyncio.sleep(DELAY)

    if blocked_ids:
        async with sessionmaker() as session:
            for i in range(0, len(blocked_ids), 500):
                await session.execute(
                    update(User).where(User.tg_id.in_(blocked_ids[i:i + 500])).values(is_blocked=True)
                )
            await session.commit()

    for admin_id in admin_ids:
        await safe_send(bot, admin_id, texts.BC_DONE.format(ok=ok, blocked=blocked, failed=failed))


def start_broadcast(*args, **kwargs) -> None:
    task = asyncio.create_task(run_broadcast(*args, **kwargs))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


def copy_sender(bot: Bot, from_chat_id: int, message_id: int, kb: InlineKeyboardMarkup | None):
    async def send(chat_id: int):
        await bot.copy_message(chat_id, from_chat_id, message_id, reply_markup=kb)
    return send
