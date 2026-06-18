from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from bot.db.repo import *
from datetime import datetime, timezone
import requests
from bot.services.city_mapper import CityMapper


logger = structlog.get_logger(__name__)



router = Router(name="start")





def utc_now() -> str:
    """Возвращает строку с текущим UTC-временем """
    now = datetime.now(timezone.utc)
    return now.replace(microsecond=0)


def build_city_id_map():
    url = 'https://api.hh.ru/areas'
    response = requests.get(url)
    data = response.json()
    city_map = {}

    def recursive_search(areas):
        for area in areas:
            # Если у зоны есть вложенные области, значит это регион, а не город
            if area.get('areas'):
                recursive_search(area['areas'])
            else:
                # Это город, добавляем его в словарь
                city_map[area['name'].lower()] = area['id']

    recursive_search(data)
    return city_map




@router.message(CommandStart())
async def start(message: Message, session: AsyncSession) -> None:
    logger.info(
        "user_start_bot",
        user_id = message.from_user.id,
        username=message.from_user.username,
        command = "/start"
    )
    await message.answer(
      "Привет! Я бот для поиска вакансий.\n"
        "Используй /set_filter чтобы настроить параметры,\n"
        "/get_jobs чтобы получить вакансии сейчас.\n"
        "/show_filters чтобы установить фильтры"
    )
    
    print(utc_now)

    user = await save_user(
        session=session,
        tg_id=message.from_user.id,
        username=message.from_user.username,
        last_seen_in_bot=utc_now(),
        created_at=utc_now(),
        name=message.from_user.first_name,
    )
    
    await CityMapper.load_cities()

    



    



@router.message(Command("help"))
async def help(message: Message) -> None:
    await message.answer("доступные команды" \
    "........")