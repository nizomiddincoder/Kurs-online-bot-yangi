"""Admin sozlamalari: matnlar, tariflar, Senior limiti, guruh qo'shish."""
from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import texts
from config import Config
from db.models import Group
from db.repo import get_user
from filters import IsAdmin
from handlers.common import menu_for
from keyboards.inline import tariff_choice_kb
from keyboards.reply import cancel_kb
from services.chats import bot_rights_problem
from services.common import esc, fmt_money
from services.courses import assign_waiting
from services.settings import get_text, get_tariff, set_setting

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

TEXT_COMMANDS = {"setgift": "gift_text", "setlesson": "lesson_text", "setabout": "about_text"}


class EditText(StatesGroup):
    text = State()


class EditTariff(StatesGroup):
    price = State()
    desc = State()


async def _done(message: Message, session: AsyncSession, config: Config, text: str):
    admin = await get_user(session, message.from_user.id)
    await message.answer(text, reply_markup=menu_for(admin, config, message.from_user.id))


# ---------------- Matnlar: /setgift /setlesson /setabout ----------------
@router.message(Command(*TEXT_COMMANDS), F.chat.type == ChatType.PRIVATE)
async def edit_text_start(message: Message, command: CommandObject, state: FSMContext, session: AsyncSession):
    key = TEXT_COMMANDS[command.command.lower()]
    await state.set_state(EditText.text)
    await state.update_data(key=key)
    await message.answer(texts.ASK_NEW_TEXT, reply_markup=cancel_kb())
    await message.answer(await get_text(session, key), disable_web_page_preview=True)


@router.message(EditText.text, F.text)
async def edit_text_save(message: Message, state: FSMContext, session: AsyncSession, config: Config):
    key = (await state.get_data())["key"]
    await state.clear()
    await set_setting(session, key, message.html_text)
    await _done(message, session, config, texts.TEXT_SAVED)


# ---------------- Tariflar: /settariff ----------------
@router.message(Command("settariff"), F.chat.type == ChatType.PRIVATE)
async def tariff_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(texts.CHOOSE_TARIFF, reply_markup=tariff_choice_kb())


@router.callback_query(F.data.startswith("st:"))
async def tariff_chosen(cb: CallbackQuery, state: FSMContext, session: AsyncSession, config: Config):
    code = cb.data.split(":", 1)[1]
    if code not in texts.TARIFF_NAMES:
        await cb.answer()
        return
    t = await get_tariff(session, config, code)
    await state.set_state(EditTariff.price)
    await state.update_data(tariff=code)
    await cb.message.answer(
        texts.ASK_TARIFF_PRICE.format(title=t["title"], price=fmt_money(t["price"])), reply_markup=cancel_kb()
    )
    await cb.answer()


@router.message(EditTariff.price, F.text)
async def tariff_price(message: Message, state: FSMContext, session: AsyncSession, config: Config):
    raw = message.text.strip().replace(" ", "")
    if raw != "-":
        if not raw.isdigit() or int(raw) <= 0:
            await message.answer(texts.BAD_NUMBER)
            return
        await state.update_data(price=int(raw))
    t = await get_tariff(session, config, (await state.get_data())["tariff"])
    await state.set_state(EditTariff.desc)
    await message.answer(texts.ASK_TARIFF_DESC.format(desc=t["desc"]))


@router.message(EditTariff.desc, F.text)
async def tariff_desc(message: Message, state: FSMContext, session: AsyncSession, config: Config):
    data = await state.get_data()
    await state.clear()
    code = data["tariff"]
    if "price" in data:
        await set_setting(session, f"tariff_{code}_price", str(data["price"]))
    if message.text.strip() != "-":
        await set_setting(session, f"tariff_{code}_desc", message.html_text)
    t = await get_tariff(session, config, code)
    await _done(message, session, config, texts.TARIFF_SAVED.format(title=t["title"], price=fmt_money(t["price"]), desc=t["desc"]))


@router.message(Command("setseniorlimit"))
async def senior_limit(message: Message, command: CommandObject, session: AsyncSession):
    arg = (command.args or "").strip()
    if not arg.isdigit():
        await message.answer(texts.SENIOR_LIMIT_USAGE)
        return
    await set_setting(session, "senior_limit", arg)
    await message.answer(texts.SENIOR_LIMIT_SAVED.format(limit=int(arg)))


# ---------------- Guruh qo'shish: /addgroup ----------------
@router.message(Command("addgroup"))
async def add_group(message: Message, command: CommandObject, session: AsyncSession, bot: Bot, config: Config):
    args = (command.args or "").split()
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        chat_id = message.chat.id
    else:
        if not args or not args[0].lstrip("-").isdigit():
            await message.answer(texts.ADDGROUP_USAGE)
            return
        chat_id = int(args.pop(0))

    tariff = args[0].lower() if args else "any"
    if tariff not in texts.GROUP_TARIFFS:
        await message.answer(texts.ADDGROUP_BAD_TARIFF)
        return
    capacity = int(args[1]) if len(args) > 1 and args[1].isdigit() else 20

    try:
        chat = await bot.get_chat(chat_id)
    except Exception:
        await message.answer(texts.ADDGROUP_NO_ACCESS)
        return
    if await bot_rights_problem(bot, chat_id):
        await message.answer(texts.ADDGROUP_NOT_ADMIN)
        return

    group = await session.scalar(select(Group).where(Group.chat_id == chat_id))
    if group is None:
        group = Group(chat_id=chat_id, title=chat.title or str(chat_id), members_count=0)
        session.add(group)
    group.title = chat.title or group.title
    group.tariff = tariff
    group.capacity = capacity
    group.active = True
    await session.commit()

    assigned = await assign_waiting(bot, session, config)
    await message.answer(texts.ADDGROUP_OK.format(
        title=esc(group.title), tariff=texts.GROUP_TARIFFS[tariff], capacity=capacity,
        members=group.members_count, assigned=assigned,
    ))
