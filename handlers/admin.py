"""Admin panel: statistika, Excel, tarqatish, kutilayotgan to'lovlar, qidiruv, guruhlar."""
from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import texts
from config import Config
from db.models import Group
from db.repo import (
    find_users, get_subscription, get_user, list_pending_payments, count_pending_payments,
    user_enrollments, user_purchases,
)
from filters import IsAdmin
from handlers.common import menu_for
from keyboards.inline import (
    admin_panel_kb, bc_audience_kb, bc_confirm_kb, bc_skip_kb, confirm_cancel_kb, groups_kb,
    pending_list_kb, user_manage_kb,
)
from keyboards.reply import cancel_kb
from services.broadcast import copy_sender, count_audience, start_broadcast
from services.common import esc, fmt_date, fmt_money, now_utc, user_card
from services.reports import build_leads_xlsx, build_stats
from services.subscriptions import cancel_subscription, deliver_channel_access, extend_subscription, send_channel_link

router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE, IsAdmin())
router.callback_query.filter(IsAdmin())


class Search(StatesGroup):
    query = State()


class Bc(StatesGroup):
    content = State()
    button = State()
    confirm = State()


@router.message(Command("admin"))
@router.message(F.text == texts.BTN_ADMIN)
async def admin_panel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(texts.ADMIN_PANEL, reply_markup=admin_panel_kb())


@router.callback_query(F.data == "adm:stats")
async def stats(cb: CallbackQuery, session: AsyncSession, config: Config):
    await cb.answer()
    await cb.message.answer(await build_stats(session, config))


@router.callback_query(F.data == "adm:export")
async def export(cb: CallbackQuery, session: AsyncSession):
    await cb.answer("⏳")
    data, count = await build_leads_xlsx(session)
    filename = f"lidlar_{now_utc():%Y%m%d}.xlsx"
    await cb.message.answer_document(BufferedInputFile(data, filename), caption=texts.EXPORT_CAPTION.format(count=count))


@router.callback_query(F.data == "adm:pending")
async def pending(cb: CallbackQuery, session: AsyncSession):
    await cb.answer()
    payments = await list_pending_payments(session)
    if not payments:
        await cb.message.answer(texts.NO_PENDING)
        return
    await cb.message.answer(
        texts.PENDING_LIST.format(count=await count_pending_payments(session)),
        reply_markup=pending_list_kb(payments),
    )


# ---------------- Guruhlar ----------------
async def _groups_text(session: AsyncSession) -> tuple[str, InlineKeyboardMarkup | None]:
    groups = list(await session.scalars(select(Group).order_by(Group.id)))
    if not groups:
        return texts.GROUPS_EMPTY + texts.ADDGROUP_USAGE, None
    lines = [
        texts.GROUP_LINE.format(
            icon="🟢" if g.active else "⚪️", title=esc(g.title), tariff=texts.GROUP_TARIFFS.get(g.tariff, g.tariff),
            members=g.members_count, capacity=g.capacity,
        ) for g in groups
    ]
    return "\n".join(lines) + texts.GROUPS_HINT, groups_kb(groups)


@router.message(Command("groups"))
async def groups_cmd(message: Message, session: AsyncSession):
    text, kb = await _groups_text(session)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "adm:groups")
async def groups_cb(cb: CallbackQuery, session: AsyncSession):
    await cb.answer()
    text, kb = await _groups_text(session)
    await cb.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("gt:"))
async def group_toggle(cb: CallbackQuery, session: AsyncSession):
    group = await session.get(Group, int(cb.data.split(":")[1]))
    if group:
        group.active = not group.active
        await session.commit()
    text, kb = await _groups_text(session)
    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()


# ---------------- Foydalanuvchini qidirish ----------------
@router.callback_query(F.data == "adm:search")
async def search_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(Search.query)
    await cb.message.answer(texts.ASK_SEARCH, reply_markup=cancel_kb())
    await cb.answer()


async def _user_info(session: AsyncSession, user) -> str:
    sub = await get_subscription(session, user.id)
    if sub is None:
        sub_text = texts.SUB_STATUS_NONE
    elif sub.status == "active" and sub.end_at > now_utc():
        sub_text = texts.SUB_ACTIVE_TILL.format(end=fmt_date(sub.end_at))
    else:
        sub_text = texts.SUB_STATUS_OTHER.format(status=sub.status, end=fmt_date(sub.end_at))
    courses = ", ".join(
        f"{texts.TARIFF_NAMES[e.tariff]} ({esc(e.group.title) if e.group else e.status})"
        for e in await user_enrollments(session, user.id)
    ) or "—"
    purchases = ", ".join(
        f"{texts.PRODUCT_TITLES.get(p.product, p.product)} — {fmt_money(p.amount)} ({fmt_date(p.decided_at)})"
        for p in await user_purchases(session, user.id)
    ) or "—"
    return texts.SEARCH_RESULT.format(
        user=user_card(user), created=fmt_date(user.created_at), sub=sub_text, courses=courses, purchases=purchases
    )


@router.message(Search.query, F.text)
async def search_query(message: Message, state: FSMContext, session: AsyncSession, config: Config):
    users = await find_users(session, message.text)
    if not users:
        await message.answer(texts.SEARCH_NOT_FOUND)
        return
    await state.clear()
    admin = await get_user(session, message.from_user.id)
    await message.answer("🔎", reply_markup=menu_for(admin, config, message.from_user.id))
    for user in users:
        await message.answer(await _user_info(session, user), reply_markup=user_manage_kb(user.tg_id))


@router.callback_query(F.data.startswith("um:"))
async def user_manage(cb: CallbackQuery, session: AsyncSession, bot: Bot, config: Config):
    _, action, tg_id = cb.data.split(":")
    user = await get_user(session, int(tg_id))
    if user is None:
        await cb.answer(texts.USER_NOT_FOUND, show_alert=True)
        return

    if action in ("ext30", "ext7"):
        sub = await extend_subscription(session, user, 30 if action == "ext30" else 7)
        await deliver_channel_access(bot, session, config, user, sub, by_admin=True)
        await cb.answer(texts.ADMIN_SUB_EXTENDED.format(end=fmt_date(sub.end_at)), show_alert=True)
    elif action == "link":
        await send_channel_link(bot, session, config, user, texts.CHANNEL_LINK)
        await cb.answer(texts.ADMIN_LINK_SENT, show_alert=True)
    elif action == "cancel":
        await cb.message.answer(texts.CONFIRM_SUB_CANCEL, reply_markup=confirm_cancel_kb(user.tg_id))
        await cb.answer()
        return
    elif action == "cancelok":
        await cancel_subscription(bot, session, config, user)
        await cb.message.edit_text(texts.ADMIN_SUB_CANCELLED)
        await cb.answer()
        return

    try:
        await cb.message.edit_text(await _user_info(session, user), reply_markup=user_manage_kb(user.tg_id))
    except Exception:
        pass


# ---------------- Xabar tarqatish ----------------
@router.callback_query(F.data == "adm:bc")
async def bc_start(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.answer(texts.BC_CHOOSE_AUDIENCE, reply_markup=bc_audience_kb())
    await cb.answer()


@router.callback_query(F.data.startswith("bca:"))
async def bc_audience(cb: CallbackQuery, state: FSMContext, session: AsyncSession):
    audience = cb.data.split(":", 1)[1]
    if audience not in texts.BC_AUDIENCES:
        await cb.answer()
        return
    if await count_audience(session, audience) == 0:
        await cb.answer(texts.BC_EMPTY, show_alert=True)
        return
    await state.set_state(Bc.content)
    await state.update_data(audience=audience)
    await cb.message.answer(texts.BC_ASK_CONTENT, reply_markup=cancel_kb())
    await cb.answer()


@router.message(Bc.content)
async def bc_content(message: Message, state: FSMContext):
    await state.update_data(from_chat_id=message.chat.id, message_id=message.message_id)
    await state.set_state(Bc.button)
    await message.answer(texts.BC_ASK_BUTTON, reply_markup=bc_skip_kb())


def _button_kb(button: list | None) -> InlineKeyboardMarkup | None:
    if not button:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=button[0], url=button[1])]])


async def _bc_preview(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    await state.set_state(Bc.confirm)
    try:
        await bot.copy_message(message.chat.id, data["from_chat_id"], data["message_id"], reply_markup=_button_kb(data.get("button")))
    except Exception:
        # Noto'g'ri havola va h.k. — tugmani olib tashlaymiz
        await state.update_data(button=None)
        await message.answer(texts.BC_BAD_BUTTON)
        await state.set_state(Bc.button)
        return
    count = await count_audience(session, data["audience"])
    await message.answer(
        texts.BC_PREVIEW.format(audience=texts.BC_AUDIENCES[data["audience"]], count=count),
        reply_markup=bc_confirm_kb(),
    )


@router.message(Bc.button, F.text)
async def bc_button(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    parts = [p.strip() for p in message.text.split("|", 1)]
    if len(parts) != 2 or not parts[0] or not parts[1].startswith(("http://", "https://", "tg://")):
        await message.answer(texts.BC_BAD_BUTTON)
        return
    await state.update_data(button=parts[:2])
    await _bc_preview(message, state, session, bot)


@router.callback_query(Bc.button, F.data == "bc:skip")
async def bc_skip(cb: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    await state.update_data(button=None)
    await cb.answer()
    await _bc_preview(cb.message, state, session, bot)


@router.callback_query(Bc.confirm, F.data == "bc:go")
async def bc_go(cb: CallbackQuery, state: FSMContext, bot: Bot, sessionmaker: async_sessionmaker,
                session: AsyncSession, config: Config):
    data = await state.get_data()
    await state.clear()
    await cb.message.edit_reply_markup(reply_markup=None)
    start_broadcast(
        bot, sessionmaker, [cb.from_user.id], data["audience"],
        copy_sender(bot, data["from_chat_id"], data["message_id"], _button_kb(data.get("button"))),
    )
    admin = await get_user(session, cb.from_user.id)
    await cb.message.answer(texts.BC_STARTED, reply_markup=menu_for(admin, config, cb.from_user.id))
    await cb.answer()


@router.callback_query(F.data == "bc:cancel")
async def bc_cancel(cb: CallbackQuery, state: FSMContext, session: AsyncSession, config: Config):
    await state.clear()
    await cb.message.edit_reply_markup(reply_markup=None)
    admin = await get_user(session, cb.from_user.id)
    await cb.message.answer(texts.CANCELLED, reply_markup=menu_for(admin, config, cb.from_user.id))
    await cb.answer()
