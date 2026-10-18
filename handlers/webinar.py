"""Webinar voronkasi: kod so'z, taklif tugmalari va admin buyruqlari (/stats /broadcast /export /hot)."""
import json

from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.filters import BaseFilter, Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

import texts
from config import Config
from db.repo import get_user
from filters import IsAdmin
from handlers.common import menu_for
from keyboards.inline import bc_audience_kb
from keyboards.reply import cancel_kb
from services.common import esc, now_utc
from services.funnel import offer_view, send_bonus, start_offer
from services.reports import build_leads_csv, build_stats, hot_leads
from services.settings import delete_setting, set_setting

router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE)


class CodewordFilter(BaseFilter):
    """Xabar kod so'zga teng bo'lsa (katta-kichik harf farqsiz)."""

    async def __call__(self, message: Message, config: Config) -> bool:
        word = (config.codeword or "").strip().casefold()
        return bool(word) and (message.text or "").strip().casefold() == word


@router.message(F.text, CodewordFilter())
async def codeword(message: Message, state: FSMContext, session: AsyncSession, bot: Bot, config: Config):
    user = await get_user(session, message.from_user.id)
    if user is None or not user.registered:
        await message.answer(texts.NEED_START)
        return
    await state.clear()
    first_time = not user.webinar_watched
    user.webinar_watched = True
    user.codeword_at = user.codeword_at or now_utc()
    await session.commit()
    await start_offer(session, config, user)  # 48 soatlik shaxsiy taklif (faqat birinchi marta boshlanadi)

    if first_time:
        await message.answer(texts.CODEWORD_ACCEPTED)
        await send_bonus(bot, session, message.chat.id)
    text, kb = await offer_view(session, config, user)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "offer:show")
async def show_offer(cb: CallbackQuery, session: AsyncSession, config: Config):
    user = await get_user(session, cb.from_user.id)
    if user is None:
        await cb.answer(texts.NEED_START, show_alert=True)
        return
    text, kb = await offer_view(session, config, user)
    await cb.message.answer(text, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "premium:gone")
async def premium_gone(cb: CallbackQuery):
    await cb.answer(texts.PREMIUM_GONE_ALERT, show_alert=True)


# ---------------- Admin buyruqlari ----------------
@router.message(Command("stats"), IsAdmin())
async def stats_cmd(message: Message, session: AsyncSession, config: Config):
    await message.answer(await build_stats(session, config))


@router.message(Command("broadcast"), IsAdmin())
async def broadcast_cmd(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(texts.BC_CHOOSE_AUDIENCE, reply_markup=bc_audience_kb())


@router.message(Command("export"), IsAdmin())
async def export_cmd(message: Message, session: AsyncSession):
    data, count = await build_leads_csv(session)
    await message.answer_document(
        BufferedInputFile(data, f"foydalanuvchilar_{now_utc():%Y%m%d}.csv"),
        caption=texts.CSV_CAPTION.format(count=count),
    )


@router.message(Command("hot"), IsAdmin())
async def hot_cmd(message: Message, session: AsyncSession):
    users = await hot_leads(session)
    if not users:
        await message.answer(texts.HOT_EMPTY)
        return
    chunk = texts.HOT_HEAD.format(count=len(users))
    for u in users:
        line = texts.HOT_LINE.format(
            tg_id=u.tg_id, name=esc(u.full_name or u.tg_id), phone=esc(u.phone or "—"),
            username=f" · @{esc(u.username)}" if u.username else "", problem=esc((u.problem or "—")[:200]),
        )
        if len(chunk) + len(line) > 3800:  # Telegram xabar limiti
            await message.answer(chunk)
            chunk = ""
        chunk += line
    await message.answer(chunk)


class BonusFile(StatesGroup):
    waiting = State()


@router.message(Command("setbonusfile"), IsAdmin())
async def bonus_file_start(message: Message, command: CommandObject, state: FSMContext, session: AsyncSession,
                           config: Config):
    if (command.args or "").strip().lower() == "off":
        await delete_setting(session, "bonus_file")
        await message.answer(texts.BONUS_FILE_REMOVED)
        return
    await state.set_state(BonusFile.waiting)
    await message.answer(texts.ASK_BONUS_FILE, reply_markup=cancel_kb())


@router.message(BonusFile.waiting, IsAdmin())
async def bonus_file_save(message: Message, state: FSMContext, session: AsyncSession, config: Config):
    if message.photo:
        media = {"type": "photo", "file_id": message.photo[-1].file_id}
    elif message.video:
        media = {"type": "video", "file_id": message.video.file_id}
    elif message.document:
        media = {"type": "document", "file_id": message.document.file_id}
    else:
        await message.answer(texts.BONUS_FILE_WRONG)
        return
    media["caption"] = message.html_text if message.caption else ""
    await set_setting(session, "bonus_file", json.dumps(media))
    await state.clear()
    admin = await get_user(session, message.from_user.id)
    await message.answer(texts.BONUS_FILE_SAVED, reply_markup=menu_for(admin, config, message.from_user.id))
