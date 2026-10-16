"""Admin o'zgartiradigan sozlamalar (settings jadvali)."""
from sqlalchemy.ext.asyncio import AsyncSession

import texts
from config import Config
from db.models import Setting
from db.repo import senior_seats_used

TEXT_KEYS = {
    "gift_text": texts.DEFAULT_GIFT,
    "lesson_text": texts.DEFAULT_LESSON,
    "about_text": texts.DEFAULT_ABOUT,
}


async def get_setting(session: AsyncSession, key: str, default: str | None = None) -> str | None:
    row = await session.get(Setting, key)
    return row.value if row else default


async def set_setting(session: AsyncSession, key: str, value: str) -> None:
    row = await session.get(Setting, key)
    if row:
        row.value = value
    else:
        session.add(Setting(key=key, value=value))
    await session.commit()


async def get_text(session: AsyncSession, key: str) -> str:
    return await get_setting(session, key, TEXT_KEYS[key])


def _default_price(config: Config, tariff: str) -> int:
    return {"basic": config.tariff_basic, "middle": config.tariff_middle, "senior": config.tariff_senior}[tariff]


async def get_tariff(session: AsyncSession, config: Config, tariff: str) -> dict:
    price = await get_setting(session, f"tariff_{tariff}_price")
    desc = await get_setting(session, f"tariff_{tariff}_desc", texts.DEFAULT_TARIFF_DESC[tariff])
    return {
        "code": tariff,
        "title": texts.TARIFF_NAMES[tariff],
        "price": int(price) if price else _default_price(config, tariff),
        "desc": desc,
    }


async def get_senior_limit(session: AsyncSession, config: Config) -> int:
    value = await get_setting(session, "senior_limit")
    return int(value) if value else config.senior_limit


async def senior_is_full(session: AsyncSession, config: Config) -> bool:
    return await senior_seats_used(session) >= await get_senior_limit(session, config)


async def product_price(session: AsyncSession, config: Config, product: str) -> int:
    if product == "paid_channel":
        return config.paid_channel_price
    return (await get_tariff(session, config, product.removeprefix("tariff_")))["price"]
