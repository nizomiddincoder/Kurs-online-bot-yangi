"""Kontent: post tayyorlash va kanallar / guruhlar / bot foydalanuvchilariga joylash."""
import html
import json
import logging
import re

from aiohttp import web
from sqlalchemy import select

import texts
from db.models import Group
from db.models import Post as PostRecord
from services.broadcast import count_audience, start_broadcast
from services.common import fmt_dt
from services.posting import MediaItem, Post, send_post
from services.tg_html import SAFE_URL, sanitize
from web.common import BOT, CFG, SM, bad_request

log = logging.getLogger(__name__)

PHOTO_LIMIT = 10 * 1024 * 1024
VIDEO_LIMIT = 50 * 1024 * 1024
_titles: dict = {}


async def _chat_title(bot, chat_id, fallback: str) -> str:
    if chat_id not in _titles:
        try:
            _titles[chat_id] = (await bot.get_chat(chat_id)).title or fallback
        except Exception:
            return fallback
    return _titles[chat_id]


async def _chat_targets(request: web.Request) -> list[dict]:
    bot, cfg = request.app[BOT], request.app[CFG]
    targets = [
        {"key": "free", "chat_id": cfg.free_channel_id, "kind": "Bepul kanal",
         "title": await _chat_title(bot, cfg.free_channel_id, "Bepul kanal")},
        {"key": "paid", "chat_id": cfg.paid_channel_id, "kind": "Pullik kanal",
         "title": await _chat_title(bot, cfg.paid_channel_id, "Pullik kanal")},
    ]
    async with request.app[SM]() as s:
        for g in await s.scalars(select(Group).where(Group.active.is_(True)).order_by(Group.id)):
            targets.append({"key": f"group:{g.id}", "chat_id": g.chat_id, "kind": "Kurs guruhi", "title": g.title})
    return targets


async def get_targets(request: web.Request) -> web.Response:
    targets = [{k: v for k, v in t.items() if k != "chat_id"} for t in await _chat_targets(request)]
    async with request.app[SM]() as s:
        audiences = [
            {"key": k, "title": _clean(v), "count": await count_audience(s, k)} for k, v in texts.BC_AUDIENCES.items()
        ]
    return web.json_response({"targets": targets, "audiences": audiences, "admins": list(request.app[CFG].admin_ids)})


def _clean(title: str) -> str:
    """Panel uchun: matn boshidagi emojini olib tashlaydi (panelda ikonkalar ishlatiladi)."""
    return re.sub(r"^[^\w«]+", "", title)


def _parse_buttons(raw: str) -> list[list[dict]] | str:
    try:
        rows = json.loads(raw or "[]")
    except ValueError:
        return "Tugmalar noto'g'ri"
    result = []
    for row in rows:
        clean = []
        for b in row:
            text, url = str(b.get("text", "")).strip(), str(b.get("url", "")).strip()
            if not text and not url:
                continue
            if not text or len(text) > 64:
                return "Tugma matni bo'sh yoki juda uzun"
            if not SAFE_URL.match(url):
                return f"«{text}» tugmasining havolasi https:// bilan boshlanishi kerak"
            clean.append({"text": text, "url": url})
        if clean:
            result.append(clean)
    return result


async def create_post(request: web.Request) -> web.Response:
    form = await request.post()
    buttons = _parse_buttons(form.get("buttons"))
    if isinstance(buttons, str):
        return bad_request(buttons)

    media = []
    for f in form.getall("files", []):
        if not getattr(f, "file", None):
            continue
        data = f.file.read()
        kind = "video" if (f.content_type or "").startswith("video/") else "photo"
        if len(data) > (VIDEO_LIMIT if kind == "video" else PHOTO_LIMIT):
            return bad_request(f"{f.filename}: fayl juda katta (rasm ≤10 MB, video ≤50 MB)")
        media.append(MediaItem(kind=kind, data=data, filename=f.filename or kind))

    post = Post(
        html=sanitize(form.get("html") or ""), media=media, buttons=buttons,
        silent=form.get("silent") == "1", no_preview=form.get("no_preview") == "1",
    )
    error = post.validate()
    if error:
        return bad_request(error)

    bot, cfg = request.app[BOT], request.app[CFG]
    results = []

    # Test: faqat adminlarga
    if form.get("test") == "1":
        for admin_id in cfg.admin_ids:
            try:
                await send_post(bot, admin_id, post)
                results.append({"title": f"Admin {admin_id}", "ok": True})
            except Exception as e:
                results.append({"title": f"Admin {admin_id}", "ok": False, "info": str(e)})
        return web.json_response({"results": results})

    try:
        keys = set(json.loads(form.get("targets") or "[]"))
    except ValueError:
        return bad_request("Joylash manzillari noto'g'ri")
    if not keys:
        return bad_request("Qayerga joylashni tanlang")

    for t in await _chat_targets(request):
        if t["key"] not in keys:
            continue
        name = f"{t['kind']}: {t['title']}"
        try:
            await send_post(bot, t["chat_id"], post)
            results.append({"title": name, "ok": True})
        except Exception as e:
            log.warning("Post %s ga joylanmadi: %s", name, e)
            results.append({"title": name, "ok": False, "info": str(e)})

    if "bot" in keys:
        audience = form.get("audience") or "all"
        if audience not in texts.BC_AUDIENCES:
            return bad_request("Auditoriya noto'g'ri")
        async with request.app[SM]() as s:
            count = await count_audience(s, audience)
        start_broadcast(
            bot, request.app[SM], list(cfg.admin_ids), audience,
            lambda chat_id: send_post(bot, chat_id, post),
        )
        results.append({
            "title": f"Bot foydalanuvchilari — {_clean(texts.BC_AUDIENCES[audience])} ({count} kishi)",
            "ok": True, "info": "Fonda yuborilmoqda. Tugagach Telegram'da hisobot keladi.",
        })

    async with request.app[SM]() as s:
        s.add(PostRecord(
            text=post.html, media_count=len(media),
            targets=json.dumps([r["title"] for r in results], ensure_ascii=False),
            results=json.dumps(results, ensure_ascii=False),
        ))
        await s.commit()
    return web.json_response({"results": results})


async def history(request: web.Request) -> web.Response:
    async with request.app[SM]() as s:
        rows = await s.scalars(select(PostRecord).order_by(PostRecord.id.desc()).limit(30))
        return web.json_response([
            {
                "id": p.id, "date": fmt_dt(p.created_at), "media_count": p.media_count,
                "text": html.unescape(re.sub(r"<[^>]+>", "", p.text))[:200],
                "results": json.loads(p.results or "[]"),
            }
            for p in rows
        ])


def setup(app: web.Application) -> None:
    app.router.add_get("/api/targets", get_targets)
    app.router.add_post("/api/posts", create_post)
    app.router.add_get("/api/posts", history)
