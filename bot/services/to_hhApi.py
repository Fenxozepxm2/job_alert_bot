import asyncio

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
from typing import Dict, List, Optional, Any
from bot.db.repo import get_user_filters
from bot.services.city_mapper import CityMapper
from urllib.parse import urlencode





# Маппинг для опыта работы
EXPERIENCE_MAP = {
    "Без опыта": "noExperience",
    "от 1 до 3": "between1And3",
    "от 3 до 6": "between3And6",
    "Более 6": "moreThan6"
}

# Маппинг для графика работы 
SCHEDULE_MAP = {
    "5/2": "fullDay",
    "2/2": "shift",
    "3/3": "shift",
    "Свободный": "free",
    "6/1": "fullDay",  # в API нет точного соответствия, берём fullDay как ближайшее
    "4/2": "shift",
    "3/2": "shift",
    "4/3": "shift",
    "4/4": "shift",
    "1/3": "shift",
    "2/1": "shift",
    "1/2": "shift"
}

# Маппинг для формата работы 
WORKFORMAT_MAP = {
    "Удалённо": "remote",
    "На месте работодателя": "office",
    "Гибрид": "hybrid",
    "Разъездной": "mobile"
}


async def filters_to_params_hh_api(message: Message, session: AsyncSession, page: int = 0 ):
    params: Dict[str, any] = {}

    tg_id = message.from_user.id
    user_filters = await get_user_filters(session,tg_id)

    # для поиска (text)
    search_parts = []
    if user_filters.get("specialization"):
        search_parts.append(user_filters["specialization"])
    if user_filters.get("find_key_words"):
        search_parts.extend(user_filters["find_key_words"])
    if search_parts:
        params["text"] = " ".join(search_parts)

    # для региона (area)
    city = user_filters.get("city")
    if city:
        city_id = CityMapper.get_city_id(city)
        if city_id:
            params["area"] = city_id


    # ЗАРПЛАТА (salary)
    # Если есть обе границы, передаем ТОЛЬКО salary_from и salary_to
    if user_filters.get("salary_from") and user_filters.get("salary_to"):
        params["salary_from"] = int(user_filters["salary_from"])
        params["salary_to"] = int(user_filters["salary_to"])
        params["only_with_salary"] = True
    # Если есть только нижняя граница
    elif user_filters.get("salary_from"):
        params["salary"] = int(user_filters["salary_from"])
        params["only_with_salary"] = True
    # Если есть только верхняя граница
    elif user_filters.get("salary_to"):
        params["salary"] = int(user_filters["salary_to"])
        params["only_with_salary"] = True
    else:
        params["only_with_salary"] = False




    # опыт работы (experience)
    if user_filters.get("exp"):
        exp_val = user_filters.get("exp")
        for i in exp_val:
            if i in EXPERIENCE_MAP:
                params["experience"] = []
                params["experience"].append(EXPERIENCE_MAP[i])
    
    

    # График работы (schedule)
    # Обработка графиков работы пользователя (5/2, 2/2 и т.д.) !!!!доработать!!!!
    params["schedule"] = []
    if user_filters.get("schedule"):
        sched_val = user_filters.get("schedule")
        for i in sched_val:
            if i in SCHEDULE_MAP:
                if SCHEDULE_MAP[i] not in params["schedule"]:
                    
                    params["schedule"].append(SCHEDULE_MAP[i])

    # Обработка формата работы (Удалённо)
    if user_filters.get("workformat"):
        work_formats = user_filters.get("workformat")
        if "Удалённо" in work_formats:
            if "remote" not in params["schedule"]:
                params["schedule"].append("remote")

    # Если список schedule остался пустым, удаляем ключ, чтобы не отправлять пустой параметр в API
    if not params["schedule"]:
        del params["schedule"]


    # ТУТ КОРОЧЕ СДЕЛАТЬ ОБРАБОТКУ ИСКЛЮЧАЮЩИЙ СЛОВ, ПОКА ЧТО ВПАДЛУ


    

    params["per_page"] = 50  # Берём оптимальный размер пачки (максимум у HH — 100)
    params["page"] = page    # Теперь страница динамическая

    # Очищаем от пустых значений
    params = {k: v for k, v in params.items() if v is not None and v != "" and v != []}

    # ИСПРАВЛЕНИЕ ДЛЯ aiohttp: Конвертируем True/False в строки "true"/"false"
    for k, v in params.items():
        if isinstance(v, bool):
            params[k] = "true" if v else "false"

    print(params)

    return params
        


import asyncio
import aiohttp
from typing import Dict, Any

class HHAPI:
    BASE_URL = "https://api.hh.ru"
    
    # Полная копия заголовков реального браузера Google Chrome на Windows 11
    
    @staticmethod
    async def format_vacancies(vac: dict) -> dict:
        id_vac = vac.get("id")
        name = vac.get("name")
        vac_url = vac.get("alternate_url")
        published_at = vac.get("published_at")
        created_at = vac.get("created_at")
        
        # Извлечение понятного текстового описания опыта
        exp = vac.get("experience", {}).get("name", "не требуется")
        
        salary_data = vac.get("salary")
        salary_str = "не указана"
        if salary_data:
            sal_from = f"от {salary_data.get('from')}" if salary_data.get('from') else ""
            sal_to = f"до {salary_data.get('to')}" if salary_data.get('to') else ""
            currency = salary_data.get('currency', '')
            salary_str = f"{sal_from} {sal_to} {currency}".strip()
        
        city = vac.get("area", {}).get("name")
        id_employer = vac.get("employer", {}).get("id")
        name_employer = vac.get("employer", {}).get("name")

        vaca = {
            "id_vac": id_vac,
            "name": name,
            "vac_url": vac_url,
            "published_at": published_at,
            "created_at": created_at,
            "exp": exp,
            "salary": salary_str,
            "city": city,
            "id_employer": id_employer,
            "name_employer": name_employer,
        }

        # Флаг IT-аккредитации
        accredited_it_employer = vac.get("employer", {}).get("accredited_it_employer")
        if accredited_it_employer:
            vaca["accredited_it_employer"] = accredited_it_employer

        address = vac.get("address")
        if address and address.get("city"):
            vaca["address"] = address.get("city")

        # Формируем контент с новыми стилями Telegram (Rich Text HTML)
        it_badge = " <mark>[IT-аккредитованная компания]</mark>" if vaca.get("accredited_it_employer") else ""
        
        # Используем теги <h1> для крупного заголовка и <hr> для линии-разделителя
        html_content = (
            f"<h1>💼 {vaca['name']}</h1>"
            f"<hr>"
            f"<p>🏢 <b>Компания:</b> {vaca['name_employer']}{it_badge}</p>"
            f"<p>💰 <b>Зарплата:</b> {vaca['salary']}</p>"
            f"<p>📍 <b>Город:</b> {vaca['city']}</p>"
            f"<p>⏳ <b>Опыт:</b> {vaca['exp']}</p>"
            f"<br>"
            f"<p>🔗 <a href='{vaca['vac_url']}'>Открыть вакансию на HH.ru</a></p>"
        )
        
        vaca["html_content"] = html_content
        
        
        return vaca






    @staticmethod
    async def search_vacancies(params: Dict[str, Any], access_token: str, session: AsyncSession, tg_id: int) -> Dict[str, Any]:
        url = f"{HHAPI.BASE_URL}/vacancies"
        
        flat_params = []
        for key, value in params.items():
            if isinstance(value, list):
                for item in value:
                    flat_params.append((key, item))
            else:
                flat_params.append((key, value))
        

        headers = {
            "User-Agent": "JobParserBot/1.0 (ваш_контактный_email@gmail.com)",
            "Authorization": f"Bearer {access_token}"
        }

        print("🔍 Отправляем запрос:")
        print(f"URL: {url}")
        print(f"Параметры: {flat_params}")
        print(f"Полный URL с параметрами: {url}?{urlencode(flat_params)}")
        print(f"Заголовки (токен скрыт): { {k: v[:10]+'...' if k == 'Authorization' else v for k, v in headers.items()} }")

        # ВАЖНО: trust_env=False заставляет эту сессию игнорировать Happ VPN
        async with aiohttp.ClientSession(headers=headers, trust_env=False) as htpp_session:
            await asyncio.sleep(1) 
            async with htpp_session.get(url, params=flat_params) as response:
                if response.status == 200:
                    data =  await response.json()

                    viewed_vac_ids = await get_viewed_vacancy_ids(session, tg_id)

                    raw_vacan = data.get("items", [])

                    filtered_vacan = [
                        vac for vac in raw_vacan
                        if str(vac.get("id")) not in viewed_vac_ids   
                    ]


                    data["items"] = filtered_vacan

                    return data

                else:
                    error_text = await response.text()
                    raise Exception(f"Ошибка API hh.ru: {response.status}. Ответ: {error_text}")
                
    @staticmethod
    async def test_connection():
        url = "https://api.hh.ru/vacancies"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://hh.ru/",
        }
        async with aiohttp.ClientSession(headers=headers, trust_env=False) as session:
            async with session.get(url, params={}) as response:
                print(await response.text())


