"""Umumiy yordamchi funksiyalar: vaqt, formatlash, xavfsiz xabar yuborish."""
import asyncio
import html
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter

import texts

log = logging.getLogger(__name__)

_TZ = ZoneInfo("Asia/Tashkent")


def set_timezone(name: str) -> None:
    global _TZ
    _TZ = ZoneInfo(name)


def get_tz() -> ZoneInfo:
    return _TZ


def now_utc() -> datetime:
    """Bazada vaqt UTC (tzinfo'siz) saqlanadi."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_local(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc).astimezone(_TZ)


def fmt_dt(dt: datetime | None) -> str:
    return to_local(dt).strftime("%d.%m.%Y %H:%M") if dt else "—"


def fmt_date(dt: datetime | None) -> str:
    return to_local(dt).strftime("%d.%m.%Y") if dt else "—"


def fmt_money(n: int | None) -> str:
    return f"{int(n or 0):,}".replace(",", " ")


def esc(value) -> str:
    return html.escape(str(value or ""))


def user_card(user) -> str:
    """Admin uchun foydalanuvchi ma'lumoti (HTML)."""
    return texts.USER_CARD.format(
        name=esc(user.full_name) or "—",
        phone=esc(user.phone) or "—",
        username=f"@{esc(user.username)}" if user.username else "—",
        tg_id=user.tg_id,
        segment=texts.SEGMENTS.get(user.segment or "", "—"),
        source=esc(user.source) or "—",
    )


async def safe_send(bot: Bot, chat_id: int, text: str, **kwargs):
    """Xabar yuboradi; bloklangan / xato bo'lsa None qaytaradi."""
    for _ in range(2):
        try:
            return await bot.send_message(chat_id, text, **kwargs)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
        except TelegramForbiddenError:
            log.info("Foydalanuvchi %s botni bloklagan", chat_id)
            return None
        except TelegramBadRequest as e:
            log.warning("%s ga xabar yuborilmadi: %s", chat_id, e)
            return None
    return None
