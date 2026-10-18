"""Bir vaqtda faqat BITTA bot nusxasi Telegram'dan xabar olsin.

Railway yangi versiyani ishga tushirganda eski nusxa bir necha soniya ishlab turadi — ikkalasi
xabar olsa, foydalanuvchiga ikki marta javob boradi. PostgreSQL «advisory lock» bilan ikkinchi
nusxa birinchisi to'xtaguncha kutadi. (SQLite — lokal test, qulf kerak emas.)
"""
import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

log = logging.getLogger(__name__)
LOCK_KEY = 724_001_2026  # shu bot uchun ixtiyoriy doimiy raqam


async def acquire(engine: AsyncEngine) -> AsyncConnection | None:
    """Qulfni oladi (kerak bo'lsa kutadi). Qaytgan ulanish bot ishlagan vaqt davomida ochiq turishi kerak."""
    if not engine.url.get_backend_name().startswith("postgresql"):
        return None
    conn = await engine.connect()
    waited = 0
    while True:
        if await conn.scalar(text("SELECT pg_try_advisory_lock(:k)"), {"k": LOCK_KEY}):
            await conn.commit()
            if waited:
                log.info("Oldingi nusxa to'xtadi — bot ishga tushmoqda (%s s kutildi)", waited)
            return conn
        await conn.rollback()
        if waited % 30 == 0:
            log.warning("Botning boshqa nusxasi ishlayapti — u to'xtashini kutyapman "
                        "(Railway'da Replicas = 1 ekanini tekshiring)")
        await asyncio.sleep(3)
        waited += 3


async def release(conn: AsyncConnection | None) -> None:
    if conn is None:
        return
    try:
        await conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": LOCK_KEY})
        await conn.close()
    except Exception:
        pass  # ulanish yopilsa, qulf o'zi bo'shaydi
