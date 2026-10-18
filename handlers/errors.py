"""Barcha xatolar logga yoziladi va adminlarga yuboriladi."""
import logging
import traceback

from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ErrorEvent

import texts
from config import Config
from services.common import esc
from services.notify import notify_admins

log = logging.getLogger(__name__)
router = Router()


# Zararsiz holatlar: tugma ikki marta bosilgan, eski tugma bosilgan va h.k. — xato emas
HARMLESS = (
    "message is not modified",
    "query is too old",
    "query id is invalid",
    "message to edit not found",
    "message to delete not found",
    "message can't be edited",
)


@router.errors()
async def on_error(event: ErrorEvent, bot: Bot, config: Config):
    if isinstance(event.exception, TelegramBadRequest) and any(
        h in str(event.exception).lower() for h in HARMLESS
    ):
        log.info("Zararsiz Telegram javobi e'tiborsiz qoldirildi: %s", event.exception)
        cb = event.update.callback_query
        if cb:
            try:
                await cb.answer()  # tugma «yuklanmoqda» holatida qolib ketmasin
            except Exception:
                pass
        return True
    log.exception("Update ishlov berishda xato: %s", event.exception, exc_info=event.exception)
    tb = "".join(traceback.format_exception(event.exception))[-1500:]
    await notify_admins(bot, config, texts.ERROR_ALERT.format(error=esc(tb)))
    return True
