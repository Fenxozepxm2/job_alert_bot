import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import load_config
from bot.logging_config import setup_logging
from bot.handlers import start_bot



async def main():
    setup_logging(log_level="DEBUG")

    config = load_config()

    bot = Bot(token=config.bot.token)
    dp = Dispatcher()

    dp.include_router(start_bot.router)

    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())