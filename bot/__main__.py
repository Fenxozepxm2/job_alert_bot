import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.types import Message, BotCommand, BotCommandScopeDefault
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import load_config
from bot.logging_config import setup_logging
from bot.handlers import start_bot
from bot.handlers import filters
from bot.midlewares.for_db import DBSessionMiddleware




async def set_commands(bot: Bot):
    comands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Получить справку"),
        BotCommand(command="show_filters", description="Фильтры"),
        BotCommand(command="set_filters", description="установить обязательные фильтры"),
    ]
    await bot.set_my_commands(comands,scope=BotCommandScopeDefault())


async def main():
    setup_logging(log_level="DEBUG")

    config = load_config()

    bot = Bot(token=config.bot.token)
    dp = Dispatcher()

    dp.update.middleware(DBSessionMiddleware())



    dp.include_router(start_bot.router)
    dp.include_router(filters.router)
    
    await set_commands(bot)
    await dp.start_polling(bot, skip_updates=True)






    
if __name__ == "__main__":
    asyncio.run(main())