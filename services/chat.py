"""Foydalanuvchi bilan yozishmalarni saqlash (web-panel chati uchun)."""
from datetime import timedelta

from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ChatMessage, User
from services.common import now_utc


def extract(message: Message) -> tuple[str | None, str | None, str | None, str | None]:
    """(matn, media turi, file_id, fayl nomi)"""
    text = message.text or message.caption
    if message.photo:
        return text, "photo", message.photo[-1].file_id, None
    for kind in ("video", "animation", "document", "audio", "voice", "video_note", "sticker"):
        media = getattr(message, kind)
        if media:
            return text, kind, media.file_id, getattr(media, "file_name", None)
    if message.contact:
        return f"📱 Kontakt: {message.contact.phone_number}", None, None, None
    if message.location:
        loc = message.location
        return f"📍 Joylashuv: https://maps.google.com/?q={loc.latitude},{loc.longitude}", None, None, None
    return text, None, None, None


async def save_incoming(session: AsyncSession, user: User, message: Message, prefix: str = "") -> ChatMessage:
    text, media_type, file_id, file_name = extract(message)
    msg = ChatMessage(
        user_id=user.id, direction="in", text=(prefix + (text or "")) or None,
        media_type=media_type, file_id=file_id, file_name=file_name,
    )
    session.add(msg)
    await session.commit()
    return msg


async def save_outgoing(
    session: AsyncSession, user: User, text: str | None, admin_name: str | None,
    media_type: str | None = None, file_id: str | None = None, file_name: str | None = None,
) -> ChatMessage:
    msg = ChatMessage(
        user_id=user.id, direction="out", text=text or None, media_type=media_type,
        file_id=file_id, file_name=file_name, admin_name=admin_name, is_read=True,
    )
    session.add(msg)
    await session.commit()
    return msg


async def recently_wrote(session: AsyncSession, user: User, minutes: int = 10) -> bool:
    """Oxirgi daqiqalarda yozganmi (avto-javobni takrorlamaslik uchun). Joriy xabar hisobga olinmaydi."""
    count = await session.scalar(
        select(func.count()).select_from(ChatMessage).where(
            ChatMessage.user_id == user.id,
            ChatMessage.created_at >= now_utc() - timedelta(minutes=minutes),
        )
    )
    return (count or 0) > 1
