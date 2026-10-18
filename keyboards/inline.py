from aiogram.types import InlineKeyboardButton as Btn
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

import texts
from services.common import fmt_money


def _kb(*rows: list[Btn]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[list(r) for r in rows])


# ---------------- Ro'yxatdan o'tish ----------------
def segments_kb() -> InlineKeyboardMarkup:
    return _kb(*[[Btn(text=name, callback_data=f"seg:{code}")] for code, name in texts.SEGMENTS.items()])


def subscribe_kb(link: str | None) -> InlineKeyboardMarkup:
    rows = []
    # Havolasiz tugmani Telegram rad etadi — havola bo'lmasa, faqat «Tekshirish» qoladi
    if link and link.startswith(("https://", "http://", "tg://")):
        rows.append([Btn(text=texts.BTN_GO_CHANNEL, url=link)])
    rows.append([Btn(text=texts.BTN_CHECK_SUB, callback_data="sub:check")])
    return _kb(*rows)


# ---------------- To'lov ----------------
def pay_kb(product: str, back: str | None = None, extra: list[Btn] | None = None) -> InlineKeyboardMarkup:
    rows = [[Btn(text=texts.BTN_SEND_RECEIPT, callback_data=f"pay:{product}")]]
    if extra:
        rows += [[b] for b in extra]
    if back:
        rows.append([Btn(text=texts.BTN_BACK, callback_data=back)])
    return _kb(*rows)


def renew_kb() -> InlineKeyboardMarkup:
    return _kb([Btn(text=texts.BTN_RENEW, callback_data="pay:paid_channel")])


def url_kb(text: str, url: str) -> InlineKeyboardMarkup:
    return _kb([Btn(text=text, url=url)])


def tariffs_kb(tariffs: list[dict], senior_full: bool, extra: list[Btn] | None = None) -> InlineKeyboardMarkup:
    rows = []
    for t in tariffs:
        if t["code"] == "senior" and senior_full:
            label = texts.TARIFF_BUTTON_FULL.format(title=t["title"])
        else:
            label = texts.TARIFF_BUTTON.format(title=t["title"], price=fmt_money(t["price"]))
        rows.append([Btn(text=label, callback_data=f"tariff:{t['code']}")])
    for b in extra or []:
        rows.append([b])
    return _kb(*rows)


# ---------------- Admin: to'lovlar ----------------
def admin_payment_kb(payment_id: int) -> InlineKeyboardMarkup:
    return _kb([
        Btn(text=texts.BTN_APPROVE, callback_data=f"pa:{payment_id}"),
        Btn(text=texts.BTN_REJECT, callback_data=f"pr:{payment_id}"),
    ])


def reject_reasons_kb(payment_id: int) -> InlineKeyboardMarkup:
    rows = [[Btn(text=name, callback_data=f"prr:{payment_id}:{code}")] for code, name in texts.REJECT_REASONS.items()]
    rows.append([Btn(text=texts.BTN_BACK, callback_data=f"pb:{payment_id}")])
    return _kb(*rows)


def reply_to_user_kb(tg_id: int) -> InlineKeyboardMarkup:
    return _kb([Btn(text=texts.BTN_REPLY, callback_data=f"rp:{tg_id}")])


# ---------------- Admin panel ----------------
def admin_panel_kb() -> InlineKeyboardMarkup:
    return _kb(
        [Btn(text=texts.BTN_ADM_STATS, callback_data="adm:stats"), Btn(text=texts.BTN_ADM_EXPORT, callback_data="adm:export")],
        [Btn(text=texts.BTN_ADM_BROADCAST, callback_data="adm:bc")],
        [Btn(text=texts.BTN_ADM_PENDING, callback_data="adm:pending")],
        [Btn(text=texts.BTN_ADM_SEARCH, callback_data="adm:search")],
        [Btn(text=texts.BTN_ADM_GROUPS, callback_data="adm:groups")],
    )


def pending_list_kb(payments) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for p in payments:
        name = (p.user.full_name or str(p.user.tg_id))[:20]
        b.button(text=f"#{p.id} {name} — {fmt_money(p.amount)}", callback_data=f"pv:{p.id}")
    b.adjust(1)
    return b.as_markup()


def bc_audience_kb() -> InlineKeyboardMarkup:
    return _kb(*[[Btn(text=name, callback_data=f"bca:{code}")] for code, name in texts.BC_AUDIENCES.items()])


def bc_skip_kb() -> InlineKeyboardMarkup:
    return _kb([Btn(text=texts.BTN_SKIP, callback_data="bc:skip")])


def bc_confirm_kb() -> InlineKeyboardMarkup:
    return _kb([Btn(text=texts.BTN_SEND, callback_data="bc:go"), Btn(text=texts.BTN_CANCEL, callback_data="bc:cancel")])


def user_manage_kb(tg_id: int) -> InlineKeyboardMarkup:
    return _kb(
        [Btn(text=texts.BTN_EXT_30, callback_data=f"um:ext30:{tg_id}"), Btn(text=texts.BTN_EXT_7, callback_data=f"um:ext7:{tg_id}")],
        [Btn(text=texts.BTN_SEND_CH_LINK, callback_data=f"um:link:{tg_id}")],
        [Btn(text=texts.BTN_SUB_CANCEL, callback_data=f"um:cancel:{tg_id}")],
        [Btn(text=texts.BTN_REPLY, callback_data=f"rp:{tg_id}")],
    )


def confirm_cancel_kb(tg_id: int) -> InlineKeyboardMarkup:
    return _kb([Btn(text=texts.BTN_CONFIRM_CANCEL, callback_data=f"um:cancelok:{tg_id}")])


def tariff_choice_kb() -> InlineKeyboardMarkup:
    return _kb(*[[Btn(text=name, callback_data=f"st:{code}")] for code, name in texts.TARIFF_NAMES.items()])


def groups_kb(groups) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for g in groups:
        icon = "🟢" if g.active else "⚪️"
        b.button(text=f"{icon} {g.title[:30]}", callback_data=f"gt:{g.id}")
    b.adjust(1)
    return b.as_markup()
