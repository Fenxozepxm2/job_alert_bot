from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, InputRichMessage
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from bot.db.repo import *
from datetime import datetime, timezone
import requests
from hh_api.client import HHClient
from bot.config import load_config
import traceback
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext


from bot.db.repo import get_user_filters
from bot.services.to_hhApi import filters_to_params_hh_api, HHAPI

config = load_config()

logger = structlog.get_logger(__name__)

router = Router(name="find_vacancies")


class VacancySearch(StatesGroup):
    browsing = State()



def get_vacancy_keyboard(id_vac: str) -> InlineKeyboardMarkup:
    # Передаем id_vac в callback_data, чтобы бот знал, какую именно вакансию лайкнули/пропустили
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❤️ Лайк", callback_data=f"like_{id_vac}"),
            InlineKeyboardButton(text="❌ Скип", callback_data=f"skip_{id_vac}")
        ],
        [
            InlineKeyboardButton(text="➡️ Далее", callback_data="next_vacancy")
        ]
    ])
    return keyboard





@router.message(Command("finder"))
async def finder(message: Message, session: AsyncSession, state: FSMContext):
    try:
        params = await filters_to_params_hh_api(message, session)
        response = await HHAPI.search_vacancies(params, config.access_token.access_token)

        vacancies = response.get("items", [])

        if not vacancies:
            await message.answer("По вашим фильтрам ничего не найдено. 🔍")
            return

        await state.update_data(vacancies=vacancies, current_index=0)
        await state.set_state(VacancySearch.browsing)

        first_item = vacancies[0]
        vac_data = await HHAPI.format_vacancies(first_item)

        rich_message = InputRichMessage(html=vac_data["html_content"])

        await message.answer_rich(
            rich_message=rich_message,
            reply_markup=get_vacancy_keyboard(vac_data['id_vac'])
        )

    except Exception as e:
        traceback.print_exc()
        error_msg = str(e)[:200]
        await message.answer(f"❌ Ошибка при поиске вакансий: {error_msg}")





@router.callback_query(VacancySearch.browsing)
async def process_vacancy_action(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    vacancies = user_data.get("vacancies", [])
    current_index = user_data.get("current_index", 0)


    if callback.data.startswith("like_"):
        vac_id = callback.data.split("_")[1]
        await callback.answer("Вакансия добавлена в избранное! ❤️")
    elif callback.data.split("_")[0] == "skip":
        await callback.answer("Вакансия пропущена ❌")
    else:
        await callback.answer()

    next_index = current_index + 1

    # 3. Проверяем, не закончились ли вакансии
    if next_index >= len(vacancies):
        await callback.message.answer("🎉 Отличные новости! Вы просмотрели все найденные вакансии.")
        await state.clear()
        return

    await state.update_data(current_index=next_index)

    next_item = vacancies[next_index]
    vac_data = await HHAPI.format_vacancies(next_item)


    page_info = f"🗂 Вакансия {next_index + 1} из {len(vacancies)}"

    html_with_counter = vac_data["html_content"] + f"<br><footer>{page_info}</footer>"

    rich_message = InputRichMessage(html=html_with_counter)

    
    try: 
        await callback.message.edit_text(
        rich_message=rich_message,
        reply_markup=get_vacancy_keyboard(vac_data['id_vac'])
        )

    except Exception as e:
        traceback.print_exc()
        await callback.message.answer("❌ Произошла ошибка при обновлении вакансии.")


    














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

    

