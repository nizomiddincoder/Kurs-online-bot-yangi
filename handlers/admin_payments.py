"""Admin: chekni tasdiqlash / rad etish."""
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

import texts
from config import Config
from db.models import Payment
from db.repo import get_user
from filters import IsAdmin
from handlers.common import menu_for
from keyboards.inline import admin_payment_kb, reject_reasons_kb
from keyboards.reply import cancel_kb
from services.payments import approve_payment, reject_payment, send_payment_card

router = Router()
router.callback_query.filter(IsAdmin())
router.message.filter(IsAdmin())


class RejectState(StatesGroup):
    reason = State()


def _pid(data: str) -> int:
    return int(data.split(":")[1])


async def _pending_or_alert(cb: CallbackQuery, session: AsyncSession, pid: int) -> Payment | None:
    payment = await session.get(Payment, pid, populate_existing=True)
    if payment is None:
        await cb.answer(texts.PAYMENT_NOT_FOUND, show_alert=True)
        return None
    if payment.status != "pending":
        await cb.answer(texts.PAYMENT_ALREADY_DECIDED.format(status=texts.PAYMENT_STATUSES[payment.status]), show_alert=True)
        try:
            await cb.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        return None
    return payment


@router.callback_query(F.data.startswith("pa:"))
async def approve(cb: CallbackQuery, session: AsyncSession, bot: Bot, config: Config):
    await cb.answer("⏳")
    ok, info = await approve_payment(bot, session, config, _pid(cb.data), cb.from_user)
    if not ok:
        await cb.message.answer(info)


@router.callback_query(F.data.startswith("pr:"))
async def reject_menu(cb: CallbackQuery, session: AsyncSession):
    pid = _pid(cb.data)
    if await _pending_or_alert(cb, session, pid):
        await cb.message.edit_reply_markup(reply_markup=reject_reasons_kb(pid))
        await cb.answer(texts.CHOOSE_REJECT_REASON)


@router.callback_query(F.data.startswith("pb:"))
async def reject_back(cb: CallbackQuery, session: AsyncSession):
    pid = _pid(cb.data)
    if await _pending_or_alert(cb, session, pid):
        await cb.message.edit_reply_markup(reply_markup=admin_payment_kb(pid))
        await cb.answer()


@router.callback_query(F.data.startswith("prr:"))
async def reject_reason(cb: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    _, pid, code = cb.data.split(":")
    pid = int(pid)
    if not await _pending_or_alert(cb, session, pid):
        return
    if code == "other":
        await state.set_state(RejectState.reason)
        await state.update_data(payment_id=pid)
        await cb.message.answer(texts.ASK_REJECT_REASON.format(id=pid), reply_markup=cancel_kb())
        await cb.answer()
        return
    ok, info = await reject_payment(bot, session, pid, cb.from_user, texts.REJECT_REASONS.get(code, code))
    await cb.answer(info, show_alert=not ok)


@router.message(RejectState.reason, F.text)
async def reject_custom(message: Message, state: FSMContext, session: AsyncSession, bot: Bot, config: Config):
    pid = (await state.get_data())["payment_id"]
    await state.clear()
    ok, info = await reject_payment(bot, session, pid, message.from_user, message.text.strip()[:500])
    await message.answer(info, reply_markup=menu_for(await get_user(session, message.from_user.id), config, message.from_user.id))


@router.callback_query(F.data.startswith("pv:"))
async def view_payment(cb: CallbackQuery, session: AsyncSession, bot: Bot):
    payment = await session.get(Payment, _pid(cb.data), populate_existing=True)
    if payment is None:
        await cb.answer(texts.PAYMENT_NOT_FOUND, show_alert=True)
        return
    await send_payment_card(bot, session, cb.from_user.id, payment)
    await cb.answer()
