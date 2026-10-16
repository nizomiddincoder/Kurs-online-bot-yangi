"""To'lov: «Chekni yuborish» → chek (rasm/fayl) → adminlarga."""
from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

import texts
from config import Config
from db.models import Payment
from db.repo import get_pending_payment, get_user
from handlers.common import menu_for
from keyboards.reply import cancel_kb
from services.common import esc, fmt_money
from services.payments import send_payment_to_admins
from services.settings import product_price, senior_is_full

router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE)


class PayStates(StatesGroup):
    receipt = State()


@router.callback_query(F.data.startswith("pay:"))
async def start_payment(cb: CallbackQuery, state: FSMContext, session: AsyncSession, config: Config):
    product = cb.data.split(":", 1)[1]
    if product not in texts.PRODUCT_TITLES:
        await cb.answer()
        return
    user = await get_user(session, cb.from_user.id)
    if user is None or not user.registered:
        await cb.answer(texts.NEED_START, show_alert=True)
        return
    if product == "tariff_senior" and await senior_is_full(session, config):
        await cb.answer(texts.SEATS_FULL_ALERT, show_alert=True)
        return
    if await get_pending_payment(session, user.id, product):
        await cb.answer(texts.PAYMENT_ALREADY_PENDING, show_alert=True)
        return

    price = await product_price(session, config, product)
    await state.set_state(PayStates.receipt)
    await state.update_data(product=product, amount=price)
    await cb.message.answer(
        texts.SEND_RECEIPT_PROMPT.format(
            product=texts.PRODUCT_TITLES[product], price=fmt_money(price),
            card=esc(config.card_number), holder=esc(config.card_holder),
        ),
        reply_markup=cancel_kb(),
    )
    await cb.answer()


@router.message(PayStates.receipt, F.photo | F.document)
async def got_receipt(message: Message, state: FSMContext, session: AsyncSession, bot: Bot, config: Config):
    data = await state.get_data()
    user = await get_user(session, message.from_user.id)
    if user is None or "product" not in data:
        await state.clear()
        await message.answer(texts.NEED_START)
        return
    if await get_pending_payment(session, user.id, data["product"]):
        await state.clear()
        await message.answer(texts.PAYMENT_ALREADY_PENDING, reply_markup=menu_for(user, config, user.tg_id))
        return

    if message.photo:
        file_id, rtype = message.photo[-1].file_id, "photo"
    else:
        file_id, rtype = message.document.file_id, "document"

    payment = Payment(
        user=user, product=data["product"], amount=data["amount"],
        receipt_file_id=file_id, receipt_type=rtype, status="pending",
    )
    session.add(payment)
    await session.commit()
    await state.clear()

    await message.answer(texts.RECEIPT_RECEIVED, reply_markup=menu_for(user, config, user.tg_id))
    await send_payment_to_admins(bot, session, config, payment)


@router.message(PayStates.receipt)
async def wrong_receipt(message: Message):
    await message.answer(texts.RECEIPT_WRONG_TYPE)
