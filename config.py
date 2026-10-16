"""ENV o'zgaruvchilarni o'qish."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _chat_id(value: str | None) -> int | str:
    value = (value or "").strip()
    try:
        return int(value)
    except ValueError:
        return value  # masalan, @kanal_username


def _int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip().replace(" ", "")
    return int(raw) if raw else default


def _db_url(raw: str | None) -> str:
    raw = (raw or "").strip()
    if not raw:
        return "sqlite+aiosqlite:///bot.db"
    # Railway "postgresql://..." beradi, bizga async drayver kerak
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://"):]
    if raw.startswith("postgresql://"):
        raw = "postgresql+asyncpg://" + raw[len("postgresql://"):]
    return raw


@dataclass
class Config:
    """Bitta umumiy obyekt. Web-panel «Sozlamalar»idan o'zgartirilsa, shu obyekt yangilanadi
    (services/runtime_config.py) — bot qayta ishga tushirilmaydi."""

    bot_token: str
    admin_ids: tuple[int, ...]
    database_url: str
    free_channel_id: int | str
    free_channel_link: str
    paid_channel_id: int
    card_number: str
    card_holder: str
    paid_channel_price: int
    tariff_basic: int
    tariff_middle: int
    tariff_senior: int
    timezone: str
    senior_limit: int
    admin_panel_password: str = ""
    panel_password_hash: str = ""  # paneldan o'zgartirilgan parol (bazada saqlanadi)
    web_port: int = 8080
    subscription_days: int = 30


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN topilmadi. .env faylini yoki Railway Variables bo'limini tekshiring.")

    admin_ids = tuple(
        int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x
    )
    if not admin_ids:
        raise RuntimeError("ADMIN_IDS bo'sh. Kamida bitta admin Telegram ID sini kiriting.")

    # Kanal ID lari bo'sh bo'lishi mumkin — ularni web-panel «Sozlamalar» bo'limida kiritsa bo'ladi
    paid = _chat_id(os.getenv("PAID_CHANNEL_ID"))
    if not isinstance(paid, int):
        paid = 0

    return Config(
        bot_token=token,
        admin_ids=admin_ids,
        database_url=_db_url(os.getenv("DATABASE_URL")),
        free_channel_id=_chat_id(os.getenv("FREE_CHANNEL_ID")) or 0,
        free_channel_link=os.getenv("FREE_CHANNEL_LINK", "").strip(),
        paid_channel_id=paid,
        card_number=os.getenv("CARD_NUMBER", "").strip(),
        card_holder=os.getenv("CARD_HOLDER", "").strip(),
        paid_channel_price=_int("PAID_CHANNEL_PRICE", 25000),
        tariff_basic=_int("TARIFF_BASIC", 250000),
        tariff_middle=_int("TARIFF_MIDDLE", 500000),
        tariff_senior=_int("TARIFF_SENIOR", 750000),
        timezone=os.getenv("TIMEZONE", "Asia/Tashkent").strip() or "Asia/Tashkent",
        senior_limit=_int("SENIOR_LIMIT", 20),
        admin_panel_password=os.getenv("ADMIN_PANEL_PASSWORD", "").strip(),
        web_port=_int("PORT", 8080),  # Railway PORT ni o'zi beradi
    )
