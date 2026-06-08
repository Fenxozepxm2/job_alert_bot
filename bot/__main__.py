import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.types import Message, BotCommand, BotCommandScopeDefault
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import load_config
from bot.logging_config import setup_logging
from bot.handlers import start_bot
from bot.handlers import filters




async def set_commands(bot: Bot):
    comands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Получить справку"),
        BotCommand(command="set_filters", description="Фильтры"),
    ]
    await bot.set_my_commands(comands,scope=BotCommandScopeDefault())


async def main():
    setup_logging(log_level="DEBUG")

    config = load_config()

    bot = Bot(token=config.bot.token)
    dp = Dispatcher()

    dp.include_router(start_bot.router)
    dp.include_router(filters.router)
    await set_commands(bot)
    await dp.start_polling(bot, skip_updates=True)


    
if __name__ == "__main__":
    asyncio.run(main())