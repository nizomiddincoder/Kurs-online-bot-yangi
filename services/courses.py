"""Online kurs: guruhga joylashtirish."""
import logging

from aiogram import Bot
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

import texts
from config import Config
from db.models import Enrollment, Group
from keyboards.inline import url_kb
from services.chats import create_join_link, is_member
from services.common import esc, safe_send, user_card
from services.notify import notify_admins

log = logging.getLogger(__name__)


async def _reserve_seat(session: AsyncSession, tariff: str) -> Group | None:
    """Tarifga mos, joyi bor birinchi guruhda bitta joyni band qiladi."""
    candidates = await session.scalars(
        select(Group)
        .where(Group.active.is_(True), or_(Group.tariff == tariff, Group.tariff == "any"))
        .order_by(Group.tariff == "any", Group.id)  # avval aniq tarifli guruhlar
    )
    for group in candidates:
        res = await session.execute(
            update(Group)
            .where(Group.id == group.id, Group.members_count < Group.capacity)
            .values(members_count=Group.members_count + 1)
        )
        if res.rowcount == 1:
            await session.commit()
            await session.refresh(group)
            return group
    return None


async def send_group_link(bot: Bot, session: AsyncSession, enrollment: Enrollment) -> None:
    group = enrollment.group
    link = await create_join_link(
        bot, session, enrollment.user, group.chat_id, kind="group", enrollment_id=enrollment.id
    )
    await safe_send(
        bot,
        enrollment.user.tg_id,
        texts.GROUP_LINK.format(group=esc(group.title)),
        reply_markup=url_kb(texts.BTN_JOIN_GROUP, link),
    )


async def assign_group(bot: Bot, session: AsyncSession, config: Config, enrollment: Enrollment) -> bool:
    """Guruh tanlab havola yuboradi. Joy bo'lmasa adminni ogohlantiradi."""
    group = await _reserve_seat(session, enrollment.tariff)
    if group is None:
        await safe_send(bot, enrollment.user.tg_id, texts.GROUP_WAIT)
        await notify_admins(
            bot, config,
            texts.ADMIN_NO_GROUP.format(tariff=texts.TARIFF_NAMES[enrollment.tariff], user=user_card(enrollment.user)),
        )
        return False
    enrollment.group_id = group.id
    enrollment.group = group
    enrollment.status = "link_sent"
    await session.commit()
    await send_group_link(bot, session, enrollment)
    return True


async def assign_waiting(bot: Bot, session: AsyncSession, config: Config) -> int:
    """Guruh kutayotgan barcha o'quvchilarni joylashtiradi (yangi guruh qo'shilganda)."""
    waiting = list(
        (await session.scalars(
            select(Enrollment).where(Enrollment.status == "waiting_group").order_by(Enrollment.id)
        )).unique()
    )
    assigned = 0
    for enr in waiting:
        group = await _reserve_seat(session, enr.tariff)
        if group is None:
            continue
        enr.group_id = group.id
        enr.group = group
        enr.status = "link_sent"
        await session.commit()
        try:
            await send_group_link(bot, session, enr)
            assigned += 1
        except Exception:
            log.exception("Enrollment #%s uchun havola yuborilmadi", enr.id)
    return assigned


async def resend_group_link(bot: Bot, session: AsyncSession, enrollment: Enrollment) -> str:
    """Foydalanuvchi so'raganda havolani yangilaydi. Natija matnini qaytaradi."""
    if enrollment.group is None:
        return texts.GROUP_WAIT
    if await is_member(bot, enrollment.group.chat_id, enrollment.user.tg_id):
        return texts.ALREADY_IN_GROUP
    await send_group_link(bot, session, enrollment)
    return ""
