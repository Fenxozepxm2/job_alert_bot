from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
import structlog


logger = structlog.get_logger(__name__)



router = Router(name="start")

@router.message(CommandStart())
async def start(message: Message) -> None:
    logger.info(
        "user_start_bot",
        user_id = message.from_user.id,
        username=message.from_user.username,
        command = "/start"
    )
    await message.answer(
      "Привет! Я бот для поиска вакансий.\n"
        "Используй /set_filter чтобы настроить параметры,\n"
        "/get_jobs чтобы получить вакансии сейчас."
    )

@router.message(Command("help"))
async def help(message: Message) -> None:
    await message.answer("доступные команды" \
    "........")