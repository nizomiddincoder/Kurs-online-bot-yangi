"""Bazadan tez-tez kerak bo'ladigan so'rovlar."""
import re

from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Enrollment, Payment, Subscription, User
from services.common import now_utc


async def get_user(session: AsyncSession, tg_id: int) -> User | None:
    return await session.scalar(select(User).where(User.tg_id == tg_id))


async def get_subscription(session: AsyncSession, user_id: int) -> Subscription | None:
    return await session.scalar(select(Subscription).where(Subscription.user_id == user_id))


async def get_active_subscription(session: AsyncSession, user_id: int) -> Subscription | None:
    return await session.scalar(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.status == "active",
            Subscription.end_at > now_utc(),
        )
    )


async def get_pending_payment(session: AsyncSession, user_id: int, product: str) -> Payment | None:
    return await session.scalar(
        select(Payment).where(
            Payment.user_id == user_id, Payment.product == product, Payment.status == "pending"
        )
    )


async def list_pending_payments(session: AsyncSession, limit: int = 30) -> list[Payment]:
    rows = await session.scalars(
        select(Payment).where(Payment.status == "pending").order_by(Payment.id).limit(limit)
    )
    return list(rows)


async def count_pending_payments(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).where(Payment.status == "pending")) or 0


async def user_purchases(session: AsyncSession, user_id: int) -> list[Payment]:
    rows = await session.scalars(
        select(Payment)
        .where(Payment.user_id == user_id, Payment.status == "approved")
        .order_by(Payment.id)
    )
    return list(rows)


async def user_enrollments(session: AsyncSession, user_id: int) -> list[Enrollment]:
    rows = await session.scalars(
        select(Enrollment).where(Enrollment.user_id == user_id).order_by(Enrollment.id)
    )
    return list(rows.unique())


async def senior_seats_used(session: AsyncSession) -> int:
    return await session.scalar(
        select(func.count()).select_from(Enrollment).where(Enrollment.tariff == "senior")
    ) or 0


async def find_users(session: AsyncSession, query: str) -> list[User]:
    """Telefon yoki Telegram ID bo'yicha qidirish."""
    digits = re.sub(r"\D", "", query)
    if not digits:
        return []
    conds = [User.phone.like(f"%{digits[-9:]}%")]
    if len(digits) <= 15:
        conds.append(User.tg_id == int(digits))
    rows = await session.scalars(select(User).where(or_(*conds)).limit(10))
    return list(rows)


def audience_query(audience: str):
    """Xabar tarqatish uchun foydalanuvchilar (tg_id) ro'yxati so'rovi."""
    q = select(User.tg_id).where(User.is_blocked.is_(False))
    if audience.startswith("seg:"):
        q = q.where(User.segment == audience.split(":", 1)[1])
    elif audience == "nopurchase":
        q = q.where(
            ~exists().where(Payment.user_id == User.id, Payment.status == "approved")
        )
    elif audience == "paid":
        q = q.where(
            exists().where(
                Subscription.user_id == User.id,
                Subscription.status == "active",
                Subscription.end_at > now_utc(),
            )
        )
    return q
