"""Botni ishga tushirish: python bot.py"""
import asyncio
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

import texts
from config import Config, load_config
from db.base import init_db, make_engine, make_sessionmaker
from handlers import get_routers
from middlewares import DbSessionMiddleware, DedupMiddleware
from services import instance_lock
from scheduler.jobs import setup_scheduler
from services.chats import bot_rights_problem
from services.common import esc, set_timezone
from services.notify import notify_admins
from services.runtime_config import load_overrides
from web.server import start_web
from web.setup import start_setup_web


def setup_logging() -> None:
    os.makedirs("logs", exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    file = RotatingFileHandler("logs/bot.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    file.setFormatter(fmt)
    logging.basicConfig(level=logging.INFO, handlers=[stream, file])
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


async def set_commands(bot: Bot, config: Config) -> None:
    await bot.set_my_commands([BotCommand(command="start", description="Botni ishga tushirish")], BotCommandScopeDefault())
    admin_cmds = [
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="admin", description="Admin panel"),
        BotCommand(command="stats", description="Statistika"),
        BotCommand(command="broadcast", description="Xabar tarqatish"),
        BotCommand(command="export", description="Foydalanuvchilar (CSV)"),
        BotCommand(command="hot", description="Issiq lidlar"),
        BotCommand(command="setbonus", description="Kod so'z bonusi matni"),
        BotCommand(command="setbonusfile", description="Bonus fayli"),
        BotCommand(command="settariff", description="Tarif tavsifi"),
        BotCommand(command="setlesson", description="Bepul dars matni"),
        BotCommand(command="setabout", description="Men haqimda matni"),
        BotCommand(command="cancel", description="Bekor qilish"),
    ]
    for admin_id in config.admin_ids:
        try:
            await bot.set_my_commands(admin_cmds, BotCommandScopeChat(chat_id=admin_id))
        except Exception:
            pass  # admin hali botga /start bosmagan


async def startup_checks(bot: Bot, config: Config) -> None:
    """Bot kanallarda admin ekanini tekshiradi."""
    chats = (("FREE_CHANNEL", config.free_channel_id), ("PAID_CHANNEL", config.paid_channel_id),
             ("COURSE_GROUP", config.course_group_id), ("RECORDINGS_CHAT", config.recordings_chat_id))
    for name, chat_id in chats:
        if not chat_id:
            await notify_admins(bot, config, texts.STARTUP_NOT_CONFIGURED.format(chat=name))
            continue
        problem = await bot_rights_problem(bot, chat_id)
        if problem:
            logging.warning("%s (%s): %s", name, chat_id, problem)
            await notify_admins(bot, config, texts.STARTUP_CHECK_FAIL.format(chat=name, detail=esc(problem)))


async def setup_mode(config: Config, reason: str) -> None:
    """Bot ishlay olmaydi — 502 o'rniga «Sozlash kerak» sahifasini ko'rsatib, kutib turadi.
    Railway'da o'zgaruvchi qo'shilgach, Railway o'zi qayta deploy qiladi."""
    for problem in config.fatal:
        logging.error("❌ SOZLAMA XATOSI: %s", problem)
    await start_setup_web(config, reason)
    await asyncio.Event().wait()


async def main() -> None:
    setup_logging()
    config = load_config()
    for warning in config.warnings:
        logging.warning("⚠️ %s", warning)
    if config.fatal:
        await setup_mode(config, "Bot ishga tushmadi: Railway'da kerakli kalit yetishmayapti yoki xato yozilgan.")
        return
    set_timezone(config.timezone)

    bot = Bot(config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True))
    try:
        me = await bot.get_me()
        logging.info("Telegram'ga ulandi: @%s", me.username)
    except TelegramUnauthorizedError:
        await bot.session.close()
        config.fatal.append("BOT_TOKEN ni Telegram qabul qilmadi — token xato yoki @BotFather'da yangilangan. "
                            "@BotFather → /mybots → bot → API Token dan to'g'ri tokenni nusxalang.")
        await setup_mode(config, "Bot ishga tushmadi: BOT_TOKEN noto'g'ri.")
        return

    engine = make_engine(config.database_url)
    try:
        await init_db(engine)
    except Exception as e:
        await bot.session.close()
        config.fatal.append(f"Ma'lumotlar bazasiga ulanib bo'lmadi ({type(e).__name__}). "
                            "DATABASE_URL aynan ${{Postgres.DATABASE_URL}} ekanini va Postgres servisi ishlayotganini tekshiring.")
        await setup_mode(config, "Bot ishga tushmadi: bazaga ulanib bo'lmadi.")
        return
    sessionmaker = make_sessionmaker(engine)
    async with sessionmaker() as session:
        await load_overrides(session, config)  # web-panel «Sozlamalar»idagi qiymatlar
    if not config.admin_ids:
        logging.warning("⚠️ Adminlar yo'q — web-panel → Sozlamalar'da admin ID sini kiriting.")

    dp = Dispatcher(storage=MemoryStorage())
    dp["config"] = config
    dp["sessionmaker"] = sessionmaker
    dp.update.outer_middleware(DedupMiddleware(sessionmaker))  # takroriy update — ikki marta javob bermaslik
    dp.update.middleware(DbSessionMiddleware(sessionmaker))
    dp.include_routers(*get_routers())

    web_runner = await start_web(bot, sessionmaker, config)
    # Boshqa nusxa ishlayotgan bo'lsa (masalan Railway yangi deploy paytida) — u to'xtaguncha kutamiz
    lock_conn = await instance_lock.acquire(engine)
    scheduler = setup_scheduler(bot, sessionmaker, config)
    scheduler.start()

    try:
        await set_commands(bot, config)
        await startup_checks(bot, config)
        await bot.delete_webhook(drop_pending_updates=False)
        logging.info("Bot ishga tushdi")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        if web_runner:
            await web_runner.cleanup()
        scheduler.shutdown(wait=False)
        await instance_lock.release(lock_conn)
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
    except RuntimeError as e:
        # Sozlama xatosi — uzun traceback o'rniga tushunarli xabar
        logging.getLogger("config").error("\n\n❌ SOZLAMA XATOSI: %s\n", e)
        sys.exit(1)
