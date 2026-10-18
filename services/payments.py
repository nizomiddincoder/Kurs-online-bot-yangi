"""To'lovlar: adminga yuborish, tasdiqlash (idempotent), rad etish."""
import json
import logging

from aiogram import Bot
from aiogram.types import User as TgUser
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

import texts
from config import Config
from db.models import Enrollment, Payment
from keyboards.inline import admin_payment_kb
from services.common import esc, fmt_dt, fmt_money, now_utc, safe_send, user_card
from services.courses import assign_group
from services.funnel import deliver_course
from services.notify import notify_admins
from services.subscriptions import deliver_channel_access, extend_subscription

log = logging.getLogger(__name__)


def payment_caption(payment: Payment, status_line: str = "") -> str:
    return texts.PAYMENT_CAPTION.format(
        id=payment.id,
        user=user_card(payment.user),
        product=texts.PRODUCT_TITLES.get(payment.product, payment.product),
        amount=fmt_money(payment.amount),
        date=fmt_dt(payment.created_at),
    ) + status_line


def _status_line(payment: Payment, admin_name: str) -> str:
    if payment.status == "approved":
        return texts.STATUS_APPROVED_BY.format(admin=esc(admin_name), date=fmt_dt(payment.decided_at))
    if payment.status == "rejected":
        return texts.STATUS_REJECTED_BY.format(
            admin=esc(admin_name), date=fmt_dt(payment.decided_at), reason=esc(payment.reject_reason)
        )
    return ""


async def send_payment_card(bot: Bot, session: AsyncSession, chat_id: int, payment: Payment) -> None:
    """Chek rasmi + ma'lumot + [Tasdiqlash][Rad etish] tugmalari."""
    pending = payment.status == "pending"
    caption = payment_caption(payment, "" if pending else "\n\n" + texts.PAYMENT_STATUSES[payment.status])
    kb = admin_payment_kb(payment.id) if pending else None
    try:
        if payment.receipt_type == "photo":
            msg = await bot.send_photo(chat_id, payment.receipt_file_id, caption=caption, reply_markup=kb)
        else:
            msg = await bot.send_document(chat_id, payment.receipt_file_id, caption=caption, reply_markup=kb)
    except Exception as e:
        log.error("To'lov #%s kartasini %s ga yuborib bo'lmadi: %s", payment.id, chat_id, e)
        return
    messages = json.loads(payment.admin_messages or "[]")
    messages.append([chat_id, msg.message_id])
    payment.admin_messages = json.dumps(messages)
    await session.commit()


async def send_payment_to_admins(bot: Bot, session: AsyncSession, config: Config, payment: Payment) -> None:
    for admin_id in config.admin_ids:
        await send_payment_card(bot, session, admin_id, payment)


async def _mark_admin_messages(bot: Bot, payment: Payment, admin_name: str) -> None:
    """Barcha adminlardagi xabarni yangilaydi: tugmalar olib tashlanadi, holat yoziladi."""
    caption = payment_caption(payment, _status_line(payment, admin_name))
    for chat_id, message_id in json.loads(payment.admin_messages or "[]"):
        try:
            await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=caption, reply_markup=None)
        except Exception as e:
            log.debug("Admin xabarini yangilab bo'lmadi: %s", e)


async def _decide(session: AsyncSession, payment_id: int, admin_id: int, status: str, reason: str | None = None) -> bool:
    """Atomar: faqat 'pending' bo'lsa holatni o'zgartiradi. Ikki marta tasdiqlashdan himoya."""
    res = await session.execute(
        update(Payment)
        .where(Payment.id == payment_id, Payment.status == "pending")
        .values(status=status, decided_at=now_utc(), decided_by=admin_id, reject_reason=reason)
    )
    await session.commit()
    return res.rowcount == 1


async def _load(session: AsyncSession, payment_id: int) -> Payment | None:
    return await session.get(Payment, payment_id, populate_existing=True)


async def approve_payment(bot: Bot, session: AsyncSession, config: Config, payment_id: int, admin: TgUser) -> tuple[bool, str]:
    if not await _decide(session, payment_id, admin.id, "approved"):
        payment = await _load(session, payment_id)
        if payment is None:
            return False, texts.PAYMENT_NOT_FOUND
        return False, texts.PAYMENT_ALREADY_DECIDED.format(status=texts.PAYMENT_STATUSES[payment.status])

    payment = await _load(session, payment_id)
    user = payment.user
    try:
        if payment.product == "paid_channel":
            sub = await extend_subscription(session, user, config.subscription_days)
            await deliver_channel_access(bot, session, config, user, sub)
        elif payment.product in ("tariff_standard", "tariff_premium"):
            # Premium → kurs guruhi, Standart → yozuvlar; ikkalasiga pullik kanal va obuna +30 kun
            await deliver_course(bot, session, config, user, payment.product.removeprefix("tariff_"), payment.id)
        else:  # eski Basic/Middle/Senior to'lovlari (o'zgarishsiz)
            tariff = payment.product.removeprefix("tariff_")
            enrollment = Enrollment(user=user, payment_id=payment.id, tariff=tariff, status="waiting_group")
            session.add(enrollment)
            await session.commit()
            await safe_send(bot, user.tg_id, texts.COURSE_APPROVED.format(tariff=texts.TARIFF_NAMES[tariff]))
            await assign_group(bot, session, config, enrollment)
    except Exception as e:
        log.exception("To'lov #%s tasdiqlangandan keyin xato", payment.id)
        await notify_admins(bot, config, texts.ADMIN_FULFILL_ERROR.format(id=payment.id, error=esc(e)))

    await _mark_admin_messages(bot, payment, admin.full_name)
    return True, texts.PAYMENT_APPROVED_OK


async def reject_payment(
    bot: Bot, session: AsyncSession, payment_id: int, admin: TgUser, reason: str
) -> tuple[bool, str]:
    if not await _decide(session, payment_id, admin.id, "rejected", reason):
        payment = await _load(session, payment_id)
        if payment is None:
            return False, texts.PAYMENT_NOT_FOUND
        return False, texts.PAYMENT_ALREADY_DECIDED.format(status=texts.PAYMENT_STATUSES[payment.status])

    payment = await _load(session, payment_id)
    await safe_send(bot, payment.user.tg_id, texts.REJECTED_USER.format(reason=esc(reason)))
    await _mark_admin_messages(bot, payment, admin.full_name)
    return True, texts.PAYMENT_REJECTED_OK
