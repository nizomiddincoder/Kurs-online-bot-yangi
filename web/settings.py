"""«⚙️ Sozlamalar»: kanal ID lari, havolalar, karta, narxlar, matnlar, panel paroli."""
import asyncio

from aiohttp import web

import texts
from services.chats import bot_rights_problem
from services.runtime_config import (
    FIELD_MAP, FIELDS, check_password, env_value, overridden, parse, reset_field, resolve_chat, save_field,
    set_password, to_text,
)
from services.settings import TEXT_KEYS, get_senior_limit, get_tariff, get_text, set_setting
from services.tg_html import plain_length, sanitize
from web.auth import set_login_cookie
from web.common import BOT, CFG, SM, bad_request

TARIFFS = ("basic", "middle", "senior")
TEXT_LABELS = {
    "gift_text": ("Bepul sovg'a (5 ta prompt)", "Kanalga obuna bo'lgandan keyin yuboriladi."),
    "lesson_text": ("«Bepul dars» bo'limi", "Dars havolasini shu yerga qo'ying (YouTube, Telegram post...)."),
    "about_text": ("«Men haqimda» bo'limi", "O'zingiz haqingizda qisqacha."),
}


async def _payload(request: web.Request) -> dict:
    cfg, bot = request.app[CFG], request.app[BOT]
    async with request.app[SM]() as s:
        over = await overridden(s)
        fields = []
        for f in FIELDS:
            env_text = to_text(env_value(f))
            fields.append({
                "name": f.name, "env": f.env, "section": f.section, "label": f.label, "help": f.help,
                "kind": f.kind, "placeholder": f.placeholder, "value": to_text(getattr(cfg, f.name)),
                "env_value": env_text, "source": "panel" if f.name in over else ("env" if env_text else "empty"),
            })
        tariffs = []
        for code in TARIFFS:
            t = await get_tariff(s, cfg, code)
            tariffs.append({"code": code, "title": t["title"], "price": t["price"], "desc": t["desc"]})
        senior_limit = await get_senior_limit(s, cfg)
        text_values = [
            {"key": k, "label": TEXT_LABELS[k][0], "help": TEXT_LABELS[k][1], "html": await get_text(s, k)}
            for k in TEXT_KEYS
        ]
    try:
        me = await bot.me()
        bot_name = f"@{me.username}"
    except Exception:
        bot_name = None
    return {
        "fields": fields,
        "tariffs": tariffs,
        "senior_limit": senior_limit,
        "texts": text_values,
        "system": {
            "bot": bot_name,
            "database": "PostgreSQL" if cfg.database_url.startswith("postgresql") else "SQLite (lokal fayl)",
            "timezone": cfg.timezone,
            "password_source": "panel" if cfg.panel_password_hash else "env",
        },
    }


async def get_settings(request: web.Request) -> web.Response:
    return web.json_response(await _payload(request))


async def _check_chat(bot, value) -> dict:
    chat_id, title, error = await resolve_chat(bot, value)
    if error:
        return {"ok": False, "id": None, "title": None, "problem": error}
    problem = await bot_rights_problem(bot, chat_id)
    return {"ok": problem is None, "id": chat_id, "title": title, "problem": problem}


async def check_chat(request: web.Request) -> web.Response:
    data = await request.json()
    try:
        value = parse(FIELD_MAP["paid_channel_id"], str(data.get("value", "")))
    except ValueError as e:
        return bad_request(str(e))
    return web.json_response(await _check_chat(request.app[BOT], value))


async def save_config(request: web.Request) -> web.Response:
    values = (await request.json()).get("values", {})
    bot, cfg = request.app[BOT], request.app[CFG]
    parsed, errors, warnings = {}, {}, {}

    for name, raw in values.items():
        field = FIELD_MAP.get(name)
        if field is None:
            continue
        try:
            value = parse(field, str(raw))
        except ValueError as e:
            errors[name] = str(e)
            continue
        if field.kind == "chat":
            check = await _check_chat(bot, value)
            if check["id"] is not None:
                value = check["id"]  # @username → raqamli ID
                if check["problem"]:
                    warnings[name] = f"«{check['title']}»: {check['problem']}"
            elif isinstance(value, str):
                errors[name] = check["problem"]
                continue
            else:
                warnings[name] = check["problem"]
        parsed[name] = value

    if errors:
        return web.json_response({"ok": False, "errors": errors}, status=400)

    async with request.app[SM]() as s:
        for name, value in parsed.items():
            if to_text(getattr(cfg, name)) != to_text(value) or name not in await overridden(s):
                await save_field(s, cfg, FIELD_MAP[name], value)
    return web.json_response({"ok": True, "warnings": warnings, "settings": await _payload(request)})


async def reset_config(request: web.Request) -> web.Response:
    field = FIELD_MAP.get((await request.json()).get("name"))
    if field is None:
        return bad_request("Noma'lum sozlama")
    async with request.app[SM]() as s:
        await reset_field(s, request.app[CFG], field)
    return web.json_response({"ok": True, "settings": await _payload(request)})


async def save_tariffs(request: web.Request) -> web.Response:
    data = await request.json()
    updates = []
    for code, t in (data.get("tariffs") or {}).items():
        if code not in TARIFFS:
            continue
        price = str(t.get("price", "")).replace(" ", "")
        if not price.isdigit() or int(price) <= 0:
            return bad_request(f"{texts.TARIFF_NAMES[code]}: narx musbat son bo'lishi kerak")
        desc = sanitize(t.get("desc") or "")
        if not desc:
            return bad_request(f"{texts.TARIFF_NAMES[code]}: tavsif bo'sh")
        if plain_length(desc) > 3000:
            return bad_request(f"{texts.TARIFF_NAMES[code]}: tavsif juda uzun")
        updates += [(f"tariff_{code}_price", price), (f"tariff_{code}_desc", desc)]
    limit = str(data.get("senior_limit", "")).strip()
    if limit:
        if not limit.isdigit():
            return bad_request("Senior joylar soni butun son bo'lishi kerak")
        updates.append(("senior_limit", limit))
    async with request.app[SM]() as s:
        for key, value in updates:
            await set_setting(s, key, value)
    return web.json_response({"ok": True, "settings": await _payload(request)})


async def save_text(request: web.Request) -> web.Response:
    data = await request.json()
    key = data.get("key")
    if key not in TEXT_KEYS:
        return bad_request("Noma'lum matn")
    value = sanitize(data.get("html") or "")
    if not value:
        return bad_request("Matn bo'sh bo'lmasin")
    if plain_length(value) > 4000:
        return bad_request(f"Matn juda uzun ({plain_length(value)} belgi, maksimum 4000)")
    async with request.app[SM]() as s:
        await set_setting(s, key, value)
    return web.json_response({"ok": True, "html": value})


async def test_text(request: web.Request) -> web.Response:
    """Matnni adminlarga sinab ko'rish uchun yuborish."""
    data = await request.json()
    value = sanitize(data.get("html") or "")
    if not value:
        return bad_request("Matn bo'sh")
    bot, cfg = request.app[BOT], request.app[CFG]
    errors = []
    for admin_id in cfg.admin_ids:
        try:
            await bot.send_message(admin_id, value)
        except Exception as e:
            errors.append(f"{admin_id}: {e}")
    if errors:
        return bad_request("Yuborilmadi — " + "; ".join(errors))
    return web.json_response({"ok": True})


async def change_password(request: web.Request) -> web.Response:
    data = await request.json()
    cfg = request.app[CFG]
    current, new, confirm = (str(data.get(k, "")) for k in ("current", "new", "confirm"))
    if not await asyncio.to_thread(check_password, cfg, current):
        await asyncio.sleep(1)
        return bad_request("Hozirgi parol noto'g'ri")
    if len(new) < 10 or new.isdigit() or new.isalpha():
        return bad_request("Yangi parol kamida 10 belgi bo'lsin va harf hamda raqam aralash bo'lsin")
    if new != confirm:
        return bad_request("Yangi parollar bir xil emas")
    async with request.app[SM]() as s:
        await set_password(s, cfg, new)
    resp = web.json_response({"ok": True})
    set_login_cookie(request, resp)  # shu brauzerda kirish saqlanib qoladi, boshqalar chiqib ketadi
    return resp


def setup(app: web.Application) -> None:
    app.router.add_get("/api/settings", get_settings)
    app.router.add_post("/api/settings/config", save_config)
    app.router.add_post("/api/settings/reset", reset_config)
    app.router.add_post("/api/settings/check-chat", check_chat)
    app.router.add_post("/api/settings/tariffs", save_tariffs)
    app.router.add_post("/api/settings/text", save_text)
    app.router.add_post("/api/settings/text/test", test_text)
    app.router.add_post("/api/settings/password", change_password)
