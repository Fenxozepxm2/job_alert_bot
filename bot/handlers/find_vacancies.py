from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from bot.db.repo import *
from datetime import datetime, timezone
import requests
from hh_api.client import HHClient
from bot.config import load_config


from bot.db.repo import get_user_filters
from bot.services.to_hhApi import filters_to_params_hh_api, HHAPI

config = load_config()

logger = structlog.get_logger(__name__)

router = Router(name="find_vacancies")


@router.message(Command("get_vacancies"))
async def get_vacancies(message: Message, session: AsyncSession):
    
    try:
        # 1. Получаем сформированные параметры
        params = await filters_to_params_hh_api(message, session)
        
        # 2. Делаем запрос к HH
        response = await HHAPI.search_vacancies(params, config.access_token.access_token)
        
        # 3. Вытаскиваем список вакансий из ответа
        vacancies = response.get("items", [])
        
        if not vacancies:
            await message.answer("По вашим фильтрам ничего не найдено. ")
            return

        # 4. Собираем красивый текст ответа, укладываясь в лимиты
        text_parts = ["* Найдена свежая подборка вакансий:*\n"]
        
        for i, vac in enumerate(vacancies[:5], 1): # Берем первые 5 вакансий для теста
            name = vac.get("name")
            company = vac.get("employer", {}).get("name", "Компания не указана")
            url = vac.get("alternate_url")
            
            # Красиво форматируем зарплату
            salary_data = vac.get("salary")
            salary_str = "не указана"
            if salary_data:
                sal_from = f"от {salary_data.get('from')}" if salary_data.get('from') else ""
                sal_to = f"до {salary_data.get('to')}" if salary_data.get('to') else ""
                salary_str = f"{sal_from} {sal_to} {salary_data.get('currency')}".strip()

            # Добавляем вакансию в список
            text_parts.append(
                f"{i}. *{name}*\n"
                f" 🏢 Компания: {company}\n"
                f" 💰 Зарплата: {salary_str}\n"
                f" 🔗 [Открыть вакансию]({url})\n"
            )
            
        # Объединяем части в одно сообщение
        final_text = "\n".join(text_parts)
        
        # Отправляем пользователю (используем Markdown, чтобы ссылки кликались)
        await message.answer(final_text, parse_mode="Markdown")

    except Exception as e:
        # Защита на случай ошибок: если текст ошибки слишком длинный, берем только первые 200 символов
        error_msg = str(e)[:200]
        await message.answer(f"❌ Ошибка при поиске вакансий: {error_msg}")

    
