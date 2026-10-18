"""Kunlik vazifa (har kuni 10:00): eslatmalar, muddati o'tganlarni chiqarish, hisobot."""
import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

import texts
from config import Config
from db.models import Payment, ProcessedUpdate, Subscription, User
from db.repo import count_pending_payments
from keyboards.inline import renew_kb
from services.chats import kick_from_chat
from services.common import esc, fmt_date, fmt_money, get_tz, now_utc, safe_send, to_local
from services.notify import notify_admins
from services.reports import active_subs_count

log = logging.getLogger(__name__)


async def check_subscriptions(bot: Bot, sessionmaker: async_sessionmaker, config: Config) -> dict:
    stats = {"reminded3": 0, "reminded1": 0, "expired": 0}
    today = datetime.now(get_tz()).date()
    now = now_utc()

    async with sessionmaker() as session:
        subs = list(await session.scalars(select(Subscription).where(Subscription.status == "active")))
        for sub in subs:
            user = sub.user
            end = fmt_date(sub.end_at)
            try:
                if sub.end_at <= now:
                    await kick_from_chat(bot, config.paid_channel_id, user.tg_id)
                    sub.status = "expired"
                    sub.expired_at = now
                    user.paid_member = False
                    await safe_send(bot, user.tg_id, texts.SUB_EXPIRED, reply_markup=renew_kb())
                    stats["expired"] += 1
                else:
                    days_left = (to_local(sub.end_at).date() - today).days
                    if days_left <= 1 and not sub.reminded_1:
                        await safe_send(bot, user.tg_id, texts.SUB_REMIND_1.format(end=end), reply_markup=renew_kb())
                        sub.reminded_1 = sub.reminded_3 = True
                        stats["reminded1"] += 1
                    elif days_left <= 3 and not sub.reminded_3:
                        await safe_send(bot, user.tg_id, texts.SUB_REMIND_3.format(end=end), reply_markup=renew_kb())
                        sub.reminded_3 = True
                        stats["reminded3"] += 1
                await session.commit()
            except Exception:
                log.exception("Obuna #%s ni tekshirishda xato", sub.id)
                await session.rollback()
            await asyncio.sleep(0.05)
    return stats


async def send_daily_report(bot: Bot, sessionmaker: async_sessionmaker, config: Config, stats: dict) -> None:
    since = now_utc() - timedelta(days=1)
    async with sessionmaker() as session:
        new_users = await session.scalar(select(func.count()).select_from(User).where(User.created_at >= since)) or 0
        new_registered = await session.scalar(
            select(func.count()).select_from(User).where(User.registered_at >= since)
        ) or 0
        approved, approved_sum = (await session.execute(
            select(func.count(), func.coalesce(func.sum(Payment.amount), 0))
            .where(Payment.status == "approved", Payment.decided_at >= since)
        )).one()
        text = texts.DAILY_REPORT.format(
            date=datetime.now(get_tz()).strftime("%d.%m.%Y"),
            new_users=new_users, new_registered=new_registered,
            approved=approved, approved_sum=fmt_money(approved_sum),
            pending=await count_pending_payments(session),
            active=await active_subs_count(session),
            **stats,
        )
    await notify_admins(bot, config, text)


async def daily_job(bot: Bot, sessionmaker: async_sessionmaker, config: Config) -> None:
    log.info("Kunlik vazifa boshlandi")
    try:
        async with sessionmaker() as session:  # eski update yozuvlarini tozalash
            await session.execute(delete(ProcessedUpdate).where(ProcessedUpdate.created_at < now_utc() - timedelta(days=2)))
            await session.commit()
        stats = await check_subscriptions(bot, sessionmaker, config)
        await send_daily_report(bot, sessionmaker, config, stats)
    except Exception as e:
        log.exception("Kunlik vazifada xato")
        await notify_admins(bot, config, texts.ERROR_ALERT.format(error=esc(repr(e))))


def setup_scheduler(bot: Bot, sessionmaker: async_sessionmaker, config: Config) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=get_tz())
    scheduler.add_job(
        daily_job,
        CronTrigger(hour=10, minute=0, timezone=get_tz()),
        kwargs={"bot": bot, "sessionmaker": sessionmaker, "config": config},
        id="daily_job",
        misfire_grace_time=3600,
        coalesce=True,
        replace_existing=True,
    )
    return scheduler
