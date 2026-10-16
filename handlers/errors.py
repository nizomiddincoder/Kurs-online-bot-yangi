"""Barcha xatolar logga yoziladi va adminlarga yuboriladi."""
import logging
import traceback

from aiogram import Bot, Router
from aiogram.types import ErrorEvent

import texts
from config import Config
from services.common import esc
from services.notify import notify_admins

log = logging.getLogger(__name__)
router = Router()


@router.errors()
async def on_error(event: ErrorEvent, bot: Bot, config: Config):
    log.exception("Update ishlov berishda xato: %s", event.exception, exc_info=event.exception)
    tb = "".join(traceback.format_exception(event.exception))[-1500:]
    await notify_admins(bot, config, texts.ERROR_ALERT.format(error=esc(tb)))
    return True
