"""Web-paneldan o'zgartiriladigan sozlamalar (ENV o'rniga bazada saqlanadi).

Qoida: panelda kiritilgan qiymat ENV dagidan ustun. «Asl qiymat» bosilsa — ENV qiymatiga qaytadi.
"""
import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass

from aiogram import Bot
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from db.models import Setting

PREFIX = "cfg:"
PASSWORD_KEY = "panel_password_hash"


@dataclass(frozen=True)
class Field:
    name: str  # Config atributi
    env: str  # ENV nomi
    section: str
    label: str
    help: str
    kind: str  # ids / chat / url / card / text / money
    placeholder: str = ""


FIELDS = [
    Field("free_channel_id", "FREE_CHANNEL_ID", "channels", "Bepul kanal ID si",
          "Obunani tekshirish uchun. Kanaldan istalgan postni botga forward qiling — bot ID ni yozib beradi. "
          "@username ham bo'ladi.", "chat", "-1001234567890 yoki @kanal"),
    Field("free_channel_link", "FREE_CHANNEL_LINK", "channels", "Bepul kanal havolasi",
          "«Kanalga o'tish» tugmasi shu havolani ochadi.", "url", "https://t.me/kanal"),
    Field("paid_channel_id", "PAID_CHANNEL_ID", "channels", "Pullik kanal ID si",
          "Yopiq kanal. Kanaldan postni botga forward qiling — bot ID ni yozib beradi.", "chat", "-1001234567890"),
    Field("admin_ids", "ADMIN_IDS", "channels", "Adminlar (Telegram ID)",
          "Vergul bilan. Chek, xabar va hisobotlar shu odamlarga keladi. O'z ID ingizni @userinfobot dan bilasiz. "
          "Har bir admin botga /start bosgan bo'lishi kerak.", "ids", "123456789, 987654321"),
    Field("card_number", "CARD_NUMBER", "payment", "Karta raqami",
          "To'lov uchun foydalanuvchiga ko'rsatiladi.", "card", "8600 1234 5678 9012"),
    Field("card_holder", "CARD_HOLDER", "payment", "Karta egasi", "Ism-familiya, kartadagi kabi.", "text",
          "Ism Familiya"),
    Field("paid_channel_price", "PAID_CHANNEL_PRICE", "payment", "Pullik kanal narxi (so'm / 30 kun)",
          "", "money", "25000"),
]
FIELD_MAP = {f.name: f for f in FIELDS}

_base: dict = {}  # ENV dan kelgan asl qiymatlar


def _remember_base(config: Config) -> None:
    if not _base:
        for f in FIELDS:
            _base[f.name] = getattr(config, f.name)


def parse(field: Field, raw: str):
    """Matnni tekshiradi va kerakli turga o'giradi. Xato bo'lsa ValueError (o'zbekcha matn bilan)."""
    raw = (raw or "").strip()
    if field.kind == "ids":
        parts = [p for p in re.split(r"[,\s;]+", raw) if p]
        if not parts:
            raise ValueError("Kamida bitta admin ID si kerak")
        if not all(p.isdigit() for p in parts):
            raise ValueError("Admin ID lari faqat raqamlardan iborat bo'lishi kerak")
        return tuple(dict.fromkeys(int(p) for p in parts))
    if field.kind == "chat":
        if not raw:
            raise ValueError("Bo'sh bo'lishi mumkin emas")
        m = re.match(r"^(?:https?://)?t\.me/([A-Za-z0-9_]{4,})/?$", raw)
        if m:
            return "@" + m.group(1)
        if re.fullmatch(r"-?\d+", raw):
            return int(raw)
        if re.fullmatch(r"@[A-Za-z0-9_]{4,}", raw):
            return raw
        raise ValueError("Kanal ID si (-100...) yoki @username bo'lishi kerak. Yopiq kanal uchun faqat ID.")
    if field.kind == "url":
        if not re.match(r"^https://t\.me/\S+$", raw):
            raise ValueError("Havola https://t.me/... ko'rinishida bo'lishi kerak")
        return raw
    if field.kind == "card":
        digits = re.sub(r"\D", "", raw)
        if len(digits) != 16:
            raise ValueError("Karta raqami 16 ta raqamdan iborat bo'lishi kerak")
        return " ".join(digits[i:i + 4] for i in range(0, 16, 4))
    if field.kind == "money":
        digits = raw.replace(" ", "")
        if not digits.isdigit() or int(digits) <= 0:
            raise ValueError("Narx musbat butun son bo'lishi kerak")
        return int(digits)
    if not raw:
        raise ValueError("Bo'sh bo'lishi mumkin emas")
    return raw[:128]


def to_text(value) -> str:
    if isinstance(value, tuple):
        return ", ".join(str(v) for v in value)
    return "" if value in (None, 0) else str(value)


async def resolve_chat(bot: Bot, value) -> tuple[int | None, str | None, str | None]:
    """(raqamli ID, nomi, xato) — @username ni raqamli ID ga aylantiradi."""
    try:
        chat = await bot.get_chat(value)
    except Exception as e:
        return None, None, f"Bot bu kanalni topa olmadi ({e}). Bot kanalga admin qilinganini tekshiring."
    return chat.id, chat.title or chat.full_name, None


async def load_overrides(session: AsyncSession, config: Config) -> None:
    """Bot ishga tushganda: bazadagi panel sozlamalarini config ga qo'llaydi."""
    _remember_base(config)
    rows = await session.scalars(select(Setting).where(Setting.key.startswith(PREFIX)))
    for row in rows:
        field = FIELD_MAP.get(row.key[len(PREFIX):])
        if field:
            try:
                setattr(config, field.name, parse(field, row.value))
            except ValueError:
                pass
    pw = await session.get(Setting, PASSWORD_KEY)
    config.panel_password_hash = pw.value if pw else ""


async def overridden(session: AsyncSession) -> set[str]:
    rows = await session.scalars(select(Setting.key).where(Setting.key.startswith(PREFIX)))
    return {k[len(PREFIX):] for k in rows}


async def save_field(session: AsyncSession, config: Config, field: Field, value) -> None:
    _remember_base(config)
    key = PREFIX + field.name
    row = await session.get(Setting, key)
    text = to_text(value)
    if row:
        row.value = text
    else:
        session.add(Setting(key=key, value=text))
    await session.commit()
    setattr(config, field.name, value)


async def reset_field(session: AsyncSession, config: Config, field: Field) -> None:
    _remember_base(config)
    await session.execute(delete(Setting).where(Setting.key == PREFIX + field.name))
    await session.commit()
    setattr(config, field.name, _base[field.name])


def env_value(field: Field):
    return _base.get(field.name)


# ---------------- Panel paroli ----------------
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()
    return f"{salt}${digest}"


def check_password(config: Config, password: str) -> bool:
    if config.panel_password_hash:
        salt, _, digest = config.panel_password_hash.partition("$")
        test = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()
        return hmac.compare_digest(test, digest)
    return bool(config.admin_panel_password) and hmac.compare_digest(
        password.encode(), config.admin_panel_password.encode()
    )


async def set_password(session: AsyncSession, config: Config, password: str) -> None:
    value = hash_password(password)
    row = await session.get(Setting, PASSWORD_KEY)
    if row:
        row.value = value
    else:
        session.add(Setting(key=PASSWORD_KEY, value=value))
    await session.commit()
    config.panel_password_hash = value
