"""Parol bilan kirish. Sessiya imzolangan cookie'da saqlanadi."""
import asyncio
import hashlib
import hmac
import logging
import time

from aiohttp import web

from services.runtime_config import check_password
from web.common import CFG

log = logging.getLogger(__name__)

COOKIE = "adm_session"
TTL = 7 * 24 * 3600  # 7 kun
PUBLIC_PATHS = {"/login", "/api/login", "/favicon.ico"}

_fails: dict[str, tuple[int, float]] = {}  # ip -> (xatolar soni, bloklanish tugashi)


def _secret(request: web.Request) -> bytes:
    cfg = request.app[CFG]
    # Parol o'zgarsa — eski kirishlar avtomatik bekor bo'ladi
    current = cfg.panel_password_hash or cfg.admin_panel_password
    return hashlib.sha256(f"{cfg.bot_token}:{current}".encode()).digest()


def set_login_cookie(request: web.Request, resp: web.Response) -> None:
    resp.set_cookie(
        COOKIE, _make_token(request), max_age=TTL, httponly=True, samesite="Lax",
        secure=request.headers.get("X-Forwarded-Proto") == "https",
    )


def _make_token(request: web.Request) -> str:
    exp = str(int(time.time()) + TTL)
    sig = hmac.new(_secret(request), exp.encode(), hashlib.sha256).hexdigest()
    return f"{exp}.{sig}"


def is_logged_in(request: web.Request) -> bool:
    token = request.cookies.get(COOKIE, "")
    exp, _, sig = token.partition(".")
    if not exp.isdigit() or int(exp) < time.time():
        return False
    good = hmac.new(_secret(request), exp.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, good)


def _ip(request: web.Request) -> str:
    return (request.headers.get("X-Forwarded-For") or request.remote or "?").split(",")[0].strip()


async def login(request: web.Request) -> web.Response:
    ip = _ip(request)
    count, until = _fails.get(ip, (0, 0))
    if until > time.time():
        return web.json_response({"error": "Juda ko'p urinish. 15 daqiqadan keyin qayta urining."}, status=429)
    if until:
        count = 0  # bloklanish muddati tugagan

    data = await request.json()
    password = str(data.get("password", ""))
    if await asyncio.to_thread(check_password, request.app[CFG], password):
        _fails.pop(ip, None)
        resp = web.json_response({"ok": True})
        set_login_cookie(request, resp)
        return resp

    count += 1
    _fails[ip] = (count, time.time() + 900 if count >= 10 else 0)
    log.warning("Admin panelga noto'g'ri parol (ip=%s, %s-urinish)", ip, count)
    await asyncio.sleep(1)
    return web.json_response({"error": "Parol noto'g'ri"}, status=401)


async def logout(request: web.Request) -> web.Response:
    resp = web.json_response({"ok": True})
    resp.del_cookie(COOKIE)
    return resp


@web.middleware
async def auth_middleware(request: web.Request, handler):
    path = request.path
    if path in PUBLIC_PATHS or path.startswith("/static/"):
        return await handler(request)
    if not is_logged_in(request):
        if path.startswith("/api/"):
            return web.json_response({"error": "Avval tizimga kiring"}, status=401)
        raise web.HTTPFound("/login")
    # CSRF himoyasi: boshqa saytlar bu sarlavhani qo'sha olmaydi
    if request.method not in ("GET", "HEAD") and request.headers.get("X-Admin") != "1":
        return web.json_response({"error": "Ruxsat yo'q"}, status=403)
    return await handler(request)


@web.middleware
async def error_middleware(request: web.Request, handler):
    try:
        return await handler(request)
    except web.HTTPException:
        raise
    except Exception as e:
        log.exception("Web-panel xatosi: %s %s", request.method, request.path)
        return web.json_response({"error": f"Server xatosi: {e}"}, status=500)


def setup(app: web.Application) -> None:
    app.router.add_post("/api/login", login)
    app.router.add_post("/api/logout", logout)
