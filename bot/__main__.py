import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.types import Message, BotCommand, BotCommandScopeDefault
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import load_config
from bot.logging_config import setup_logging
from bot.handlers import start_bot
from bot.handlers import filters
from bot.handlers import find_vacancies
from aiogram.client.session.aiohttp import AiohttpSession
from bot.midlewares.for_db import DBSessionMiddleware
from bot.services.city_mapper import CityMapper





async def set_commands(bot: Bot):
    comands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Получить справку"),
        BotCommand(command="show_filters", description="Фильтры"),
        BotCommand(command="set_filters", description="установить обязательные фильтры"),
        BotCommand(command="get_vacancies", description="получить вакансии"),

    ]
    await bot.set_my_commands(comands,scope=BotCommandScopeDefault())



async def on_startup():
    """Выполняется при старте бота."""
    print("Загрузка справочника городов...")
    await CityMapper.load_cities()
    print("Справочник городов загружен.")


async def main():
    setup_logging(log_level="DEBUG")

    config = load_config()


    bot = Bot(token=config.bot.token)
    dp = Dispatcher()

    dp.update.middleware(DBSessionMiddleware())



    dp.include_router(start_bot.router)
    dp.include_router(filters.router)
    dp.include_router(find_vacancies.router)

    

    dp.startup.register(on_startup)

    await set_commands(bot)
    await dp.start_polling(bot, skip_updates=True)






    
if __name__ == "__main__":
    asyncio.run(main())

