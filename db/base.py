from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def make_engine(url: str) -> AsyncEngine:
    kwargs = {}
    if url.startswith("postgresql"):
        kwargs.update(pool_pre_ping=True, pool_size=5, max_overflow=5)
    return create_async_engine(url, **kwargs)


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_db(engine: AsyncEngine) -> None:
    from db import models  # noqa: F401  (jadvallarni ro'yxatdan o'tkazish)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_missing_columns)


# Eski bazaga yangi ustunlarni qo'shish (create_all mavjud jadvalni o'zgartirmaydi)
NEW_COLUMNS = {
    "users": {
        "free_member": "BOOLEAN", "paid_member": "BOOLEAN", "members_checked_at": "TIMESTAMP",
        "problem": "TEXT", "webinar_watched": "BOOLEAN", "codeword_at": "TIMESTAMP",
        "offer_started_at": "TIMESTAMP", "offer_expires_at": "TIMESTAMP",
    },
}


def _add_missing_columns(conn) -> None:
    insp = inspect(conn)
    for table, columns in NEW_COLUMNS.items():
        existing = {c["name"] for c in insp.get_columns(table)}
        for name, sql_type in columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}"))
