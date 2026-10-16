"""Botni ishga tushirish: python bot.py"""
import asyncio
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

import texts
from config import Config, load_config
from db.base import init_db, make_engine, make_sessionmaker
from handlers import get_routers
from middlewares import DbSessionMiddleware
from scheduler.jobs import setup_scheduler
from services.chats import bot_rights_problem
from services.common import esc, set_timezone
from services.notify import notify_admins
from services.runtime_config import load_overrides
from web.server import start_web


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
        BotCommand(command="setgift", description="Bepul sovg'a matni"),
        BotCommand(command="setlesson", description="Bepul dars matni"),
        BotCommand(command="setabout", description="Men haqimda matni"),
        BotCommand(command="settariff", description="Tarif narxi va tavsifi"),
        BotCommand(command="setseniorlimit", description="Senior joylar soni"),
        BotCommand(command="groups", description="Guruhlar"),
        BotCommand(command="cancel", description="Bekor qilish"),
    ]
    for admin_id in config.admin_ids:
        try:
            await bot.set_my_commands(admin_cmds, BotCommandScopeChat(chat_id=admin_id))
        except Exception:
            pass  # admin hali botga /start bosmagan


async def startup_checks(bot: Bot, config: Config) -> None:
    """Bot kanallarda admin ekanini tekshiradi."""
    for name, chat_id in (("FREE_CHANNEL", config.free_channel_id), ("PAID_CHANNEL", config.paid_channel_id)):
        if not chat_id:
            await notify_admins(bot, config, texts.STARTUP_NOT_CONFIGURED.format(chat=name))
            continue
        problem = await bot_rights_problem(bot, chat_id)
        if problem:
            logging.warning("%s (%s): %s", name, chat_id, problem)
            await notify_admins(bot, config, texts.STARTUP_CHECK_FAIL.format(chat=name, detail=esc(problem)))


async def main() -> None:
    setup_logging()
    config = load_config()
    set_timezone(config.timezone)

    engine = make_engine(config.database_url)
    await init_db(engine)
    sessionmaker = make_sessionmaker(engine)
    async with sessionmaker() as session:
        await load_overrides(session, config)  # web-panel «Sozlamalar»idagi qiymatlar

    bot = Bot(config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True))
    dp = Dispatcher(storage=MemoryStorage())
    dp["config"] = config
    dp["sessionmaker"] = sessionmaker
    dp.update.middleware(DbSessionMiddleware(sessionmaker))
    dp.include_routers(*get_routers())

    scheduler = setup_scheduler(bot, sessionmaker, config)
    scheduler.start()
    web_runner = await start_web(bot, sessionmaker, config)

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
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
