from aiogram import Bot

from config import Config
from services.common import safe_send


async def notify_admins(bot: Bot, config: Config, text: str, **kwargs) -> None:
    for admin_id in config.admin_ids:
        await safe_send(bot, admin_id, text, **kwargs)
