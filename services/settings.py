"""Admin o'zgartiradigan sozlamalar (settings jadvali)."""
from sqlalchemy.ext.asyncio import AsyncSession

import texts
from config import Config
from db.models import Setting
from db.repo import senior_seats_used

TEXT_KEYS = {
    "bonus_text": texts.DEFAULT_BONUS,  # kod so'zdan keyingi bonus
    "lesson_text": texts.DEFAULT_LESSON,
    "about_text": texts.DEFAULT_ABOUT,
}

COURSE_TARIFFS = ("standard", "premium")  # hozirgi tariflar
LEGACY_TARIFFS = ("basic", "middle", "senior")  # eski to'lovlar tarixi uchun


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


async def delete_setting(session: AsyncSession, key: str) -> None:
    row = await session.get(Setting, key)
    if row:
        await session.delete(row)
        await session.commit()


async def get_text(session: AsyncSession, key: str) -> str:
    return await get_setting(session, key, TEXT_KEYS[key])


def full_price(config: Config, tariff: str) -> int:
    return {
        "standard": config.price_standard_full, "premium": config.price_premium_full,
        "basic": config.tariff_basic, "middle": config.tariff_middle, "senior": config.tariff_senior,
    }[tariff]


def offer_price(config: Config, tariff: str) -> int:
    return {"standard": config.price_standard_offer, "premium": config.price_premium_offer}.get(
        tariff, full_price(config, tariff)
    )


async def get_tariff(session: AsyncSession, config: Config, tariff: str) -> dict:
    desc = await get_setting(session, f"tariff_{tariff}_desc", texts.DEFAULT_TARIFF_DESC[tariff])
    price = full_price(config, tariff)
    if tariff in LEGACY_TARIFFS:  # eski tariflarda narx bazada saqlangan bo'lishi mumkin
        saved = await get_setting(session, f"tariff_{tariff}_price")
        price = int(saved) if saved else price
    return {"code": tariff, "title": texts.TARIFF_NAMES[tariff], "price": price,
            "offer": offer_price(config, tariff), "desc": desc}


async def get_senior_limit(session: AsyncSession, config: Config) -> int:
    value = await get_setting(session, "senior_limit")
    return int(value) if value else config.senior_limit


async def senior_is_full(session: AsyncSession, config: Config) -> bool:
    return await senior_seats_used(session) >= await get_senior_limit(session, config)


async def product_price(session: AsyncSession, config: Config, product: str, user=None) -> int:
    """To'lov summasi. Standart/Premium: taklif muddati ichida maxsus narx, keyin to'liq narx."""
    if product == "paid_channel":
        return config.paid_channel_price
    tariff = product.removeprefix("tariff_")
    if tariff in COURSE_TARIFFS:
        from services.funnel import offer_active  # aylana importdan qochish

        full = full_price(config, tariff)
        return min(offer_price(config, tariff), full) if user is not None and offer_active(user) else full
    return (await get_tariff(session, config, tariff))["price"]
