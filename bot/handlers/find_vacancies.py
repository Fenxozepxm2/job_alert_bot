from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from bot.db.repo import *
from datetime import datetime, timezone
import requests
from hh_api.client import HHClient
from bot.db.repo import get_user_filters

logger = structlog.get_logger(__name__)

router = Router(name="find_vacancies")


@router.message(Command("get_vacancies"))
async def get_vacancies(message: Message, session: AsyncSession):
    tg_id = message.from_user.id
    user_filters = await get_user_filters(session, tg_id)
    print(user_filters)
