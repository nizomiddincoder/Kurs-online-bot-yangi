"""Online chat: botga yozganlar bilan yozishma."""
import mimetypes
import re
from io import BytesIO

from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import BufferedInputFile
from aiohttp import web
from sqlalchemy import and_, case, func, or_, select, update

import texts
from db.models import ChatMessage, User
from services.chat import save_outgoing
from services.common import esc, fmt_dt
from web.common import BOT, SM, bad_request

ADMIN_NAME = "Admin (web)"
CAPTION_LIMIT = 1024


def msg_json(m: ChatMessage) -> dict:
    return {
        "id": m.id, "dir": m.direction, "text": m.text, "media_type": m.media_type,
        "file_id": m.file_id, "file_name": m.file_name, "admin": m.admin_name,
        "time": fmt_dt(m.created_at), "read": m.is_read,
    }


async def list_chats(request: web.Request) -> web.Response:
    q = (request.query.get("q") or "").strip()
    unread_expr = func.sum(
        case((and_(ChatMessage.direction == "in", ChatMessage.is_read.is_(False)), 1), else_=0)
    )
    async with request.app[SM]() as s:
        agg = (
            select(ChatMessage.user_id, func.max(ChatMessage.id).label("last_id"), unread_expr.label("unread"))
            .group_by(ChatMessage.user_id).subquery()
        )
        stmt = (
            select(User, ChatMessage, agg.c.unread)
            .join(agg, agg.c.user_id == User.id)
            .join(ChatMessage, ChatMessage.id == agg.c.last_id)
        )
        if q:
            digits = re.sub(r"\D", "", q)
            conds = [User.full_name.ilike(f"%{q}%"), User.username.ilike(f"%{q.lstrip('@')}%")]
            if digits:
                conds.append(User.phone.like(f"%{digits}%"))
            stmt = stmt.where(or_(*conds))
        rows = (await s.execute(stmt.order_by(agg.c.last_id.desc()).limit(200))).all()
        return web.json_response([
            {
                "user_id": u.id, "tg_id": u.tg_id, "name": u.full_name, "phone": u.phone,
                "username": u.username, "blocked": u.is_blocked, "unread": int(unread or 0),
                "last": msg_json(m),
            }
            for u, m, unread in rows
        ])


async def messages(request: web.Request) -> web.Response:
    user_id = int(request.match_info["user_id"])
    after = int(request.query.get("after") or 0)
    async with request.app[SM]() as s:
        user = await s.get(User, user_id)
        if user is None:
            raise web.HTTPNotFound()
        stmt = select(ChatMessage).where(ChatMessage.user_id == user_id)
        if after:
            msgs = list(await s.scalars(stmt.where(ChatMessage.id > after).order_by(ChatMessage.id)))
        else:
            msgs = list(await s.scalars(stmt.order_by(ChatMessage.id.desc()).limit(200)))[::-1]
        await s.execute(
            update(ChatMessage)
            .where(ChatMessage.user_id == user_id, ChatMessage.direction == "in", ChatMessage.is_read.is_(False))
            .values(is_read=True)
        )
        await s.commit()
        return web.json_response({
            "user": {"id": user.id, "tg_id": user.tg_id, "name": user.full_name, "phone": user.phone,
                     "username": user.username, "blocked": user.is_blocked},
            "messages": [msg_json(m) for m in msgs],
        })


async def send(request: web.Request) -> web.Response:
    user_id = int(request.match_info["user_id"])
    form = await request.post()
    text = (form.get("text") or "").strip()
    upload = form.get("file")
    if not text and not getattr(upload, "file", None):
        return bad_request("Xabar bo'sh")

    bot = request.app[BOT]
    async with request.app[SM]() as s:
        user = await s.get(User, user_id)
        if user is None:
            raise web.HTTPNotFound()
        body = f"{texts.ADMIN_REPLY_HEADER}\n{esc(text)}" if text else texts.ADMIN_REPLY_HEADER
        media_type = file_id = file_name = None
        try:
            if getattr(upload, "file", None):
                data = upload.file.read()
                file_name = upload.filename or "file"
                ctype = upload.content_type or mimetypes.guess_type(file_name)[0] or ""
                inp = BufferedInputFile(data, file_name)
                caption = body if len(text) < CAPTION_LIMIT - 30 else texts.ADMIN_REPLY_HEADER
                if ctype.startswith("image/") and not ctype.endswith("gif"):
                    msg = await bot.send_photo(user.tg_id, inp, caption=caption)
                    media_type, file_id = "photo", msg.photo[-1].file_id
                elif ctype.startswith("video/"):
                    msg = await bot.send_video(user.tg_id, inp, caption=caption)
                    media_type, file_id = "video", msg.video.file_id
                else:
                    msg = await bot.send_document(user.tg_id, inp, caption=caption)
                    media_type, file_id = "document", msg.document.file_id
                if caption != body:
                    await bot.send_message(user.tg_id, body)
            else:
                await bot.send_message(user.tg_id, body)
        except TelegramForbiddenError:
            user.is_blocked = True
            await s.commit()
            return bad_request("Foydalanuvchi botni bloklagan — xabar yetib bormadi.")
        except Exception as e:
            return bad_request(f"Yuborib bo'lmadi: {e}")

        m = await save_outgoing(s, user, text, ADMIN_NAME, media_type, file_id, file_name)
        return web.json_response(msg_json(m))


async def file_proxy(request: web.Request) -> web.Response:
    """Telegram'dagi faylni (rasm, ovoz...) brauzerda ko'rsatish."""
    bot = request.app[BOT]
    try:
        tg_file = await bot.get_file(request.match_info["file_id"])
        buf = BytesIO()
        await bot.download_file(tg_file.file_path, buf)
    except Exception as e:
        return web.json_response({"error": f"Fayl olinmadi: {e}"}, status=404)
    ctype = mimetypes.guess_type(tg_file.file_path)[0] or "application/octet-stream"
    if tg_file.file_path.endswith(".oga"):
        ctype = "audio/ogg"
    return web.Response(body=buf.getvalue(), content_type=ctype, headers={"Cache-Control": "private, max-age=86400"})


def setup(app: web.Application) -> None:
    app.router.add_get("/api/chats", list_chats)
    app.router.add_get("/api/chats/{user_id:\\d+}", messages)
    app.router.add_post("/api/chats/{user_id:\\d+}/send", send)
    app.router.add_get("/api/file/{file_id}", file_proxy)
