import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from db.models import ProcessedUpdate

log = logging.getLogger(__name__)


class DedupMiddleware(BaseMiddleware):
    """Bir xil Telegram update ikki marta ishlanmasin (masalan, bot ikki nusxada ishlab qolsa).

    update_id bazaga yoziladi; ikkinchi urinishda baza «allaqachon bor» deydi — update tashlab yuboriladi.
    Baza umumiy bo'lgani uchun bu bir nechta nusxa orasida ham ishlaydi.
    """

    def __init__(self, sessionmaker: async_sessionmaker):
        self.sessionmaker = sessionmaker

    async def __call__(self, handler, event: Update, data: dict[str, Any]) -> Any:
        try:
            async with self.sessionmaker() as session:
                session.add(ProcessedUpdate(update_id=event.update_id))
                await session.commit()
        except IntegrityError:
            log.info("Update %s allaqachon ishlangan — takrorlanmaydi", event.update_id)
            return None
        return await handler(event, data)


class DbSessionMiddleware(BaseMiddleware):
    """Har bir update uchun alohida baza sessiyasi (`session` argumenti)."""

    def __init__(self, sessionmaker: async_sessionmaker):
        self.sessionmaker = sessionmaker

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self.sessionmaker() as session:
            data["session"] = session
            return await handler(event, data)
