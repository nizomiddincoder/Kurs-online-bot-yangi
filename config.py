"""ENV o'zgaruvchilarni o'qish."""
import os
import re
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

KNOWN_VARS = (
    "BOT_TOKEN", "ADMIN_IDS", "DATABASE_URL", "ADMIN_PANEL_PASSWORD", "FREE_CHANNEL_ID", "FREE_CHANNEL_LINK",
    "PAID_CHANNEL_ID", "CARD_NUMBER", "CARD_HOLDER", "PAID_CHANNEL_PRICE", "TARIFF_BASIC", "TARIFF_MIDDLE",
    "TARIFF_SENIOR", "SENIOR_LIMIT", "TIMEZONE",
)
SYSTEM_PREFIXES = ("RAILWAY_", "PYTHON", "GPG_", "NIXPACKS", "LANG", "LC_")
SYSTEM_VARS = {"PATH", "HOME", "HOSTNAME", "PWD", "SHLVL", "TERM", "TZ", "PORT", "_"}


def _clean_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1].strip()  # "qo'shtirnoq" ichida yozilgan bo'lsa
    return value


def _normalize_env() -> None:
    """Kichik xatolarni tuzatadi: 'bot_token', 'BOT_TOKEN ' (bo'sh joy), "qo'shtirnoq" ichidagi qiymat."""
    squashed = {v.replace("_", ""): v for v in KNOWN_VARS}  # BOTTOKEN -> BOT_TOKEN
    aliases = {"ADMIN_ID": "ADMIN_IDS", "ADMINS": "ADMIN_IDS", "TOKEN": "BOT_TOKEN"}
    for key, value in list(os.environ.items()):
        canonical = re.sub(r"[\s\-]+", "_", key.strip()).upper()
        canonical = aliases.get(canonical) or squashed.get(canonical.replace("_", ""), canonical)
        if canonical not in KNOWN_VARS:
            continue
        cleaned = _clean_value(value)
        if not _clean_value(os.environ.get(canonical, "")):
            os.environ[canonical] = cleaned
        elif canonical == key:
            os.environ[key] = cleaned


_normalize_env()


REQUIRED_VARS = ("BOT_TOKEN", "ADMIN_IDS", "DATABASE_URL", "ADMIN_PANEL_PASSWORD")


def env_status() -> tuple[dict[str, bool], list[str]]:
    """Qaysi muhim o'zgaruvchilar bor (faqat NOMLARI — qiymatlar hech qayerda ko'rsatilmaydi)
    va boshqa (noma'lum) o'zgaruvchilar nomlari — xato yozilgan nomlarni topish uchun."""
    import difflib

    status = {name: bool(os.getenv(name, "").strip()) for name in REQUIRED_VARS}
    # Faqat kerakli nomlarga o'xshaganlarini ko'rsatamiz (masalan BOTTOKEN, ADMIN_ID, BOT_TOKEN_)
    others = sorted(
        k for k in os.environ
        if k not in KNOWN_VARS and k not in SYSTEM_VARS and not k.startswith(SYSTEM_PREFIXES)
        and (difflib.get_close_matches(k.upper(), REQUIRED_VARS, n=1, cutoff=0.7)
             or any(word in k.upper() for word in ("TOKEN", "ADMIN", "DATABASE", "PASSWORD")))
    )
    return status, others


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
    fatal: list = field(default_factory=list)  # bot ishga tusha olmaydigan muammolar
    warnings: list = field(default_factory=list)  # bot ishlaydi, lekin nimadir yetishmaydi


def load_config() -> Config:
    """Hech qachon yiqilmaydi. Muammolar config.fatal (bot ishlay olmaydi) va
    config.warnings (bot ishlaydi, lekin nimadir yetishmaydi) ro'yxatlariga yoziladi."""
    fatal: list[str] = []
    warnings: list[str] = []

    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        fatal.append("BOT_TOKEN kiritilmagan — @BotFather bergan tokenni Railway Variables'ga qo'shing.")
    elif not re.fullmatch(r"\d+:[\w-]{30,}", token):
        fatal.append("BOT_TOKEN noto'g'ri ko'rinishda. U @BotFather bergan to'liq matn bo'lishi kerak "
                     "(masalan 1234567890:AAH...), bo'sh joy va qo'shtirnoqsiz.")

    raw_admins = [x for x in re.split(r"[,\s;]+", os.getenv("ADMIN_IDS", "")) if x]
    admin_ids = tuple(dict.fromkeys(int(x) for x in raw_admins if x.isdigit()))
    if any(not x.isdigit() for x in raw_admins):
        warnings.append("ADMIN_IDS da raqam bo'lmagan qiymat bor — u e'tiborga olinmadi (faqat raqamli ID yozing).")
    if not admin_ids:
        warnings.append("ADMIN_IDS kiritilmagan — cheklar va xabarlar hech kimga bormaydi. "
                        "Railway Variables'ga yoki web-panel → Sozlamalar'ga admin ID sini kiriting.")

    if not os.getenv("ADMIN_PANEL_PASSWORD", "").strip():
        warnings.append("ADMIN_PANEL_PASSWORD kiritilmagan — web-panelga kirib bo'lmaydi.")
    if not os.getenv("DATABASE_URL", "").strip():
        warnings.append("DATABASE_URL kiritilmagan — vaqtinchalik SQLite ishlatilmoqda, qayta deployda "
                        "ma'lumotlar o'chadi. Railway'da: DATABASE_URL=${{Postgres.DATABASE_URL}}")

    timezone = os.getenv("TIMEZONE", "").strip() or "Asia/Tashkent"
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo(timezone)
    except Exception:
        warnings.append(f"TIMEZONE noto'g'ri ({timezone}) — Asia/Tashkent ishlatildi.")
        timezone = "Asia/Tashkent"

    # Kanal ID lari bo'sh bo'lishi mumkin — ularni web-panel «Sozlamalar» bo'limida kiritsa bo'ladi
    paid = _chat_id(os.getenv("PAID_CHANNEL_ID"))
    if not isinstance(paid, int):
        paid = 0

    def num(name: str, default: int) -> int:
        try:
            return _int(name, default)
        except ValueError:
            warnings.append(f"{name} raqam emas — standart qiymat ({default}) ishlatildi.")
            return default

    return Config(
        fatal=fatal,
        warnings=warnings,
        bot_token=token,
        admin_ids=admin_ids,
        database_url=_db_url(os.getenv("DATABASE_URL")),
        free_channel_id=_chat_id(os.getenv("FREE_CHANNEL_ID")) or 0,
        free_channel_link=os.getenv("FREE_CHANNEL_LINK", "").strip(),
        paid_channel_id=paid,
        card_number=os.getenv("CARD_NUMBER", "").strip(),
        card_holder=os.getenv("CARD_HOLDER", "").strip(),
        paid_channel_price=num("PAID_CHANNEL_PRICE", 25000),
        tariff_basic=num("TARIFF_BASIC", 250000),
        tariff_middle=num("TARIFF_MIDDLE", 500000),
        tariff_senior=num("TARIFF_SENIOR", 750000),
        timezone=timezone,
        senior_limit=num("SENIOR_LIMIT", 20),
        admin_panel_password=os.getenv("ADMIN_PANEL_PASSWORD", "").strip(),
        web_port=num("PORT", 8080),  # Railway PORT ni o'zi beradi
    )
