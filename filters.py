from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from config import Config


class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery, config: Config) -> bool:
        return event.from_user is not None and event.from_user.id in config.admin_ids
