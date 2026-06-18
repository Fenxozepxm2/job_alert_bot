from aiogram import Router, F
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
import structlog
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from bot.db.models import *
from bot.db.repo import *
from aiogram.types import CallbackQuery
from bot.states.filter_states import FilterForm
import aiohttp
from typing import Dict, List, Optional
from bot.db.repo import get_user_filters

async def filters_to_params_hh_api(message: Message, session: AsyncSession):
    params = {}
    tg_id = message.from_user.id
    user_filters = await get_user_filters(session,tg_id)


    