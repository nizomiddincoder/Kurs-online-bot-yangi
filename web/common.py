from aiogram import Bot
from aiohttp import web
from sqlalchemy.ext.asyncio import async_sessionmaker

from config import Config

BOT = web.AppKey("bot", Bot)
SM = web.AppKey("sessionmaker", async_sessionmaker)
CFG = web.AppKey("config", Config)


def bad_request(message: str) -> web.Response:
    return web.json_response({"error": message}, status=400)
