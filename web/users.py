"""Foydalanuvchilar ro'yxati, statistika, a'zolikni tekshirish, Excel."""
import re

from aiohttp import web
from sqlalchemy import and_, exists, func, or_, select

import texts
from db.models import ChatMessage, Enrollment, Group, Payment, Subscription, User
from db.repo import count_pending_payments
from services.common import fmt_date, fmt_dt, now_utc
from services.members import progress, refresh_user, start_refresh_all
from services.reports import active_subs_count, build_leads_xlsx
from web.common import BOT, CFG, SM

PAGE_SIZE = 50


def _paid(sub: Subscription | None, user: User, now) -> dict:
    if sub is None:
        status = "none"
    elif sub.status == "active" and sub.end_at > now:
        status = "active"
    else:
        status = sub.status if sub.status != "active" else "expired"
    return {"status": status, "end": fmt_date(sub.end_at) if sub else None, "member": user.paid_member}


def user_json(user: User, sub, enrollments, purchase: tuple | None, unread: int) -> dict:
    now = now_utc()
    return {
        "id": user.id,
        "tg_id": user.tg_id,
        "name": user.full_name,
        "phone": user.phone,
        "username": user.username,
        "segment": texts.SEGMENTS.get(user.segment or "", None),
        "source": user.source,
        "created": fmt_dt(user.created_at),
        "registered": user.registered,
        "blocked": user.is_blocked,
        "free_member": user.free_member,
        "checked": fmt_dt(user.members_checked_at) if user.members_checked_at else None,
        "paid": _paid(sub, user, now),
        "groups": [
            {
                "tariff": texts.TARIFF_NAMES.get(e.tariff, e.tariff),
                "title": e.group.title if e.group else None,
                "status": e.status,
            }
            for e in enrollments
        ],
        "purchases": {"count": purchase[0], "sum": purchase[1]} if purchase else {"count": 0, "sum": 0},
        "unread": unread,
    }


async def _details(session, users_subs: list[tuple]) -> list[dict]:
    ids = [u.id for u, _ in users_subs]
    if not ids:
        return []
    enr_map: dict[int, list] = {}
    for e in (await session.scalars(select(Enrollment).where(Enrollment.user_id.in_(ids)).order_by(Enrollment.id))).unique():
        enr_map.setdefault(e.user_id, []).append(e)
    purchases = {
        uid: (cnt, total) for uid, cnt, total in (await session.execute(
            select(Payment.user_id, func.count(), func.coalesce(func.sum(Payment.amount), 0))
            .where(Payment.status == "approved", Payment.user_id.in_(ids)).group_by(Payment.user_id)
        )).all()
    }
    unread = dict((await session.execute(
        select(ChatMessage.user_id, func.count())
        .where(ChatMessage.direction == "in", ChatMessage.is_read.is_(False), ChatMessage.user_id.in_(ids))
        .group_by(ChatMessage.user_id)
    )).all())
    return [user_json(u, s, enr_map.get(u.id, []), purchases.get(u.id), unread.get(u.id, 0)) for u, s in users_subs]


async def list_users(request: web.Request) -> web.Response:
    p = request.query
    page = max(1, int(p.get("page") or 1))
    now = now_utc()
    stmt = select(User, Subscription).outerjoin(Subscription, Subscription.user_id == User.id)

    if p.get("status", "registered") == "registered":
        stmt = stmt.where(User.registered.is_(True))
    q = (p.get("q") or "").strip()
    if q:
        conds = [User.full_name.ilike(f"%{q}%"), User.username.ilike(f"%{q.lstrip('@')}%")]
        digits = re.sub(r"\D", "", q)
        if digits:
            conds.append(User.phone.like(f"%{digits}%"))
            if len(digits) <= 15:
                conds.append(User.tg_id == int(digits))
        stmt = stmt.where(or_(*conds))
    if p.get("segment") in texts.SEGMENTS:
        stmt = stmt.where(User.segment == p["segment"])
    free = p.get("free")
    if free == "yes":
        stmt = stmt.where(User.free_member.is_(True))
    elif free == "no":
        stmt = stmt.where(User.free_member.is_(False))
    paid = p.get("paid")
    active = and_(Subscription.status == "active", Subscription.end_at > now)
    if paid == "active":
        stmt = stmt.where(active)
    elif paid == "expired":
        stmt = stmt.where(Subscription.id.is_not(None), ~active)
    elif paid == "none":
        stmt = stmt.where(Subscription.id.is_(None))
    group = p.get("group")
    if group == "waiting":
        stmt = stmt.where(exists().where(Enrollment.user_id == User.id, Enrollment.status == "waiting_group"))
    elif group == "any":
        stmt = stmt.where(exists().where(Enrollment.user_id == User.id))
    elif group and group.isdigit():
        stmt = stmt.where(exists().where(Enrollment.user_id == User.id, Enrollment.group_id == int(group)))

    async with request.app[SM]() as session:
        total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = (await session.execute(
            stmt.order_by(User.id.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
        )).unique().all()
        items = await _details(session, [(r[0], r[1]) for r in rows])
    return web.json_response({
        "total": total, "page": page, "pages": max(1, -(-total // PAGE_SIZE)), "items": items,
    })


async def check_user(request: web.Request) -> web.Response:
    async with request.app[SM]() as session:
        user = await session.get(User, int(request.match_info["user_id"]))
        if user is None:
            raise web.HTTPNotFound()
        await refresh_user(request.app[BOT], session, request.app[CFG], user)
        sub = await session.scalar(select(Subscription).where(Subscription.user_id == user.id))
        item = (await _details(session, [(user, sub)]))[0]
    return web.json_response(item)


async def check_all(request: web.Request) -> web.Response:
    if request.method == "POST":
        start_refresh_all(request.app[BOT], request.app[SM], request.app[CFG])
    return web.json_response(progress)


async def stats(request: web.Request) -> web.Response:
    async with request.app[SM]() as s:
        count = lambda *w: s.scalar(select(func.count()).select_from(User).where(*w))  # noqa: E731
        revenue = await s.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.status == "approved")
        )
        unread = await s.scalar(
            select(func.count(func.distinct(ChatMessage.user_id)))
            .where(ChatMessage.direction == "in", ChatMessage.is_read.is_(False))
        )
        data = {
            "total": await count(),
            "registered": await count(User.registered.is_(True)),
            "free_members": await count(User.free_member.is_(True)),
            "active_subs": await active_subs_count(s),
            "pending": await count_pending_payments(s),
            "revenue": revenue or 0,
            "unread_chats": unread or 0,
        }
    return web.json_response(data)


async def groups(request: web.Request) -> web.Response:
    async with request.app[SM]() as s:
        rows = await s.scalars(select(Group).order_by(Group.id))
        return web.json_response([
            {"id": g.id, "title": g.title, "tariff": texts.GROUP_TARIFFS.get(g.tariff, g.tariff),
             "members": g.members_count, "capacity": g.capacity, "active": g.active}
            for g in rows
        ])


async def export(request: web.Request) -> web.Response:
    async with request.app[SM]() as s:
        data, _ = await build_leads_xlsx(s)
    return web.Response(
        body=data,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="lidlar_{now_utc():%Y%m%d}.xlsx"'},
    )


def setup(app: web.Application) -> None:
    app.router.add_get("/api/stats", stats)
    app.router.add_get("/api/users", list_users)
    app.router.add_get("/api/groups", groups)
    app.router.add_get("/api/users/export.xlsx", export)
    app.router.add_route("*", "/api/users/check-all", check_all)
    app.router.add_post("/api/users/{user_id:\\d+}/check", check_user)
