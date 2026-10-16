from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

import texts


def main_menu(segment: str | None = None, is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=texts.BTN_COURSE), KeyboardButton(text=texts.BTN_PAID)],
        [KeyboardButton(text=texts.BTN_FREE_LESSON), KeyboardButton(text=texts.BTN_ABOUT)],
        [KeyboardButton(text=texts.BTN_CONTACT)],
    ]
    if segment == "biz":
        rows.append([KeyboardButton(text=texts.BTN_AI_AGENT)])
    if is_admin:
        rows.append([KeyboardButton(text=texts.BTN_ADMIN)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=texts.BTN_SEND_PHONE, request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=texts.BTN_CANCEL)]], resize_keyboard=True)
