from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from services.common import now_utc


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    full_name: Mapped[str | None] = mapped_column(String(128))
    phone: Mapped[str | None] = mapped_column(String(32), index=True)
    segment: Mapped[str | None] = mapped_column(String(16))  # smm / biz / learn
    source: Mapped[str | None] = mapped_column(String(64))  # deep-link: ig, ad1...
    registered: Mapped[bool] = mapped_column(Boolean, default=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)
    registered_at: Mapped[datetime | None] = mapped_column(DateTime)
    # Oxirgi tekshiruv natijasi (None — hali tekshirilmagan)
    free_member: Mapped[bool | None] = mapped_column(Boolean)
    paid_member: Mapped[bool | None] = mapped_column(Boolean)
    members_checked_at: Mapped[datetime | None] = mapped_column(DateTime)
    # --- Webinar voronkasi ---
    problem: Mapped[str | None] = mapped_column(Text)  # «Qaysi muammo bilan kelyapsiz?»
    webinar_watched: Mapped[bool | None] = mapped_column(Boolean, default=False)  # kod so'z yozdi
    codeword_at: Mapped[datetime | None] = mapped_column(DateTime)
    offer_started_at: Mapped[datetime | None] = mapped_column(DateTime)
    offer_expires_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)


class FunnelMark(Base):
    """Kimga qaysi avtomatik xabar yuborilgani (eslatma, follow-up). Restartdan keyin ham
    takroriy yuborilmaydi: (user_id, key) juftligi yagona."""

    __tablename__ = "funnel_marks"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_funnel_user_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    key: Mapped[str] = mapped_column(String(80))
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class ChatMessage(Base):
    """Foydalanuvchi ↔ admin yozishmalari (web-paneldagi chat)."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    direction: Mapped[str] = mapped_column(String(3))  # in / out
    text: Mapped[str | None] = mapped_column(Text)
    media_type: Mapped[str | None] = mapped_column(String(16))  # photo / video / document / voice ...
    file_id: Mapped[str | None] = mapped_column(String(256))
    file_name: Mapped[str | None] = mapped_column(String(255))
    admin_name: Mapped[str | None] = mapped_column(String(128))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)


class Post(Base):
    """Web-paneldan joylangan kontent tarixi."""

    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, default="")
    media_count: Mapped[int] = mapped_column(Integer, default=0)
    targets: Mapped[str] = mapped_column(Text, default="[]")  # JSON
    results: Mapped[str] = mapped_column(Text, default="[]")  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    product: Mapped[str] = mapped_column(String(32))  # paid_channel / tariff_basic / ...
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)  # pending/approved/rejected
    receipt_file_id: Mapped[str] = mapped_column(String(256))
    receipt_type: Mapped[str] = mapped_column(String(16))  # photo / document
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    decided_by: Mapped[int | None] = mapped_column(BigInteger)
    reject_reason: Mapped[str | None] = mapped_column(Text)
    admin_messages: Mapped[str] = mapped_column(Text, default="[]")  # [[chat_id, message_id], ...]

    user: Mapped[User] = relationship(lazy="joined")


class Subscription(Base):
    """Pullik kanal obunasi (har bir foydalanuvchiga bitta yozuv)."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    start_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    end_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)  # active/expired/cancelled
    reminded_3: Mapped[bool] = mapped_column(Boolean, default=False)
    reminded_1: Mapped[bool] = mapped_column(Boolean, default=False)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime)

    user: Mapped[User] = relationship(lazy="joined")


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    title: Mapped[str] = mapped_column(String(255))
    tariff: Mapped[str] = mapped_column(String(16), default="any")  # basic/middle/senior/any
    capacity: Mapped[int] = mapped_column(Integer, default=20)
    members_count: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class Enrollment(Base):
    """Online kursga yozilish (tasdiqlangan tarif to'lovi)."""

    __tablename__ = "enrollments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), unique=True)
    tariff: Mapped[str] = mapped_column(String(16))
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id"))
    status: Mapped[str] = mapped_column(String(16), default="waiting_group")  # waiting_group/link_sent/joined
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    joined_at: Mapped[datetime | None] = mapped_column(DateTime)

    user: Mapped[User] = relationship(lazy="joined")
    group: Mapped[Group | None] = relationship(lazy="joined")


class InviteLink(Base):
    __tablename__ = "invite_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    link: Mapped[str] = mapped_column(String(256))
    kind: Mapped[str] = mapped_column(String(16))  # channel / group
    enrollment_id: Mapped[int | None] = mapped_column(ForeignKey("enrollments.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    expire_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class ProcessedUpdate(Base):
    """Ishlangan Telegram update'lar — takroriy javobdan himoya (2 kundan eskisi o'chiriladi)."""

    __tablename__ = "processed_updates"

    update_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)


class Setting(Base):
    """Admin o'zgartiradigan matnlar va narxlar."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
