"""Web admin-panel serveri (bot bilan bitta jarayonda ishlaydi)."""
import logging
from pathlib import Path

from aiogram import Bot
from aiohttp import web
from sqlalchemy.ext.asyncio import async_sessionmaker

from config import Config
from web import auth, chat, content, settings, users
from web.common import BOT, CFG, SM

log = logging.getLogger(__name__)
STATIC = Path(__file__).parent / "static"


async def index(request: web.Request) -> web.FileResponse:
    return web.FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


async def login_page(request: web.Request):
    if auth.is_logged_in(request):
        raise web.HTTPFound("/")
    return web.FileResponse(STATIC / "login.html", headers={"Cache-Control": "no-cache"})


@web.middleware
async def no_stale_static(request: web.Request, handler):
    """Yangilangan JS/CSS darhol ishlashi uchun: brauzer har safar o'zgarganini tekshiradi."""
    resp = await handler(request)
    if request.path.startswith("/static/"):
        resp.headers["Cache-Control"] = "no-cache"
    return resp


def create_app(bot: Bot, sessionmaker: async_sessionmaker, config: Config) -> web.Application:
    app = web.Application(
        middlewares=[auth.error_middleware, no_stale_static, auth.auth_middleware],
        client_max_size=200 * 1024 * 1024,
    )
    app[BOT] = bot
    app[SM] = sessionmaker
    app[CFG] = config
    app.router.add_get("/", index)
    app.router.add_get("/login", login_page)
    app.router.add_static("/static", STATIC)
    auth.setup(app)
    users.setup(app)
    chat.setup(app)
    content.setup(app)
    settings.setup(app)
    return app


async def start_web(bot: Bot, sessionmaker: async_sessionmaker, config: Config) -> web.AppRunner | None:
    if not (config.admin_panel_password or config.panel_password_hash):
        log.warning("ADMIN_PANEL_PASSWORD berilmagan — web admin-panel o'chirilgan")
        return None
    runner = web.AppRunner(create_app(bot, sessionmaker, config), access_log=None)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", config.web_port).start()
    log.info("Web admin-panel ishga tushdi: port %s", config.web_port)
    return runner
