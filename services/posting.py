"""Kontentni (matn + rasm/video + tugmalar) istalgan chatga yuborish."""
from dataclasses import dataclass, field

from aiogram import Bot
from aiogram.types import (
    BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo,
    LinkPreviewOptions,
)

from services.tg_html import plain_length

CAPTION_LIMIT = 1024
TEXT_LIMIT = 4096


@dataclass
class MediaItem:
    kind: str  # photo / video
    data: bytes | None = None
    filename: str = "file"
    file_id: str | None = None  # birinchi yuborishdan keyin qayta yuklamaslik uchun

    def input(self):
        return self.file_id or BufferedInputFile(self.data, self.filename)


@dataclass
class Post:
    html: str = ""
    media: list[MediaItem] = field(default_factory=list)
    buttons: list[list[dict]] = field(default_factory=list)  # [[{"text":..., "url":...}], ...]
    silent: bool = False
    no_preview: bool = False

    def markup(self) -> InlineKeyboardMarkup | None:
        rows = [[InlineKeyboardButton(text=b["text"], url=b["url"]) for b in row] for row in self.buttons if row]
        return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None

    def validate(self) -> str | None:
        length = plain_length(self.html)
        if not self.html and not self.media:
            return "Matn yoki rasm qo'shing."
        if length > TEXT_LIMIT:
            return f"Matn juda uzun: {length} belgi (maksimum {TEXT_LIMIT})."
        if len(self.media) > 10:
            return "Bir postda ko'pi bilan 10 ta rasm/video bo'ladi."
        return None


def _remember(item: MediaItem, msg) -> None:
    if item.file_id:
        return
    if item.kind == "photo" and msg.photo:
        item.file_id = msg.photo[-1].file_id
    elif item.kind == "video" and msg.video:
        item.file_id = msg.video.file_id


async def send_post(bot: Bot, chat_id: int | str, post: Post) -> None:
    kb = post.markup()
    common = {"disable_notification": post.silent}
    caption_fits = plain_length(post.html) <= CAPTION_LIMIT
    text_kwargs = {**common, "link_preview_options": LinkPreviewOptions(is_disabled=post.no_preview)}

    if not post.media:
        await bot.send_message(chat_id, post.html, reply_markup=kb, **text_kwargs)
        return

    if len(post.media) == 1:
        item = post.media[0]
        caption = post.html if caption_fits else None
        send = bot.send_photo if item.kind == "photo" else bot.send_video
        msg = await send(chat_id, item.input(), caption=caption, reply_markup=kb if caption_fits else None, **common)
        _remember(item, msg)
        if not caption_fits:
            await bot.send_message(chat_id, post.html, reply_markup=kb, **text_kwargs)
        return

    # Albom: albomga tugma qo'yib bo'lmaydi — tugma/uzun matn alohida xabarda
    separate_text = bool(kb) or not caption_fits
    group = []
    for i, item in enumerate(post.media):
        cls = InputMediaPhoto if item.kind == "photo" else InputMediaVideo
        caption = post.html if (i == 0 and not separate_text and post.html) else None
        group.append(cls(media=item.input(), caption=caption))
    msgs = await bot.send_media_group(chat_id, group, **common)
    for item, msg in zip(post.media, msgs):
        _remember(item, msg)
    if separate_text:
        await bot.send_message(chat_id, post.html or "👇", reply_markup=kb, **text_kwargs)
