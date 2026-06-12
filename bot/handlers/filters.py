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



logger = structlog.get_logger(__name__)
router = Router(name="Filters")





def normalize_number(raw: str) -> int:
    """
    Преобразует строку с числом в int, игнорируя пробелы, запятые и другие нецифровые символы.
    Примеры: '7 000' -> 7000, '7,000' -> 7000, '7 500' -> 7500
    """
    # Оставляем только цифры
    cleaned = ''.join(ch for ch in raw if ch.isdigit())
    if not cleaned:
        raise ValueError("Нет цифр в строке")
    return int(cleaned)

async def show_shedule_choise(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    filters = data.get("filters", {})
    current_schedule = filters.get("schedule", [])

    schedule_options = ["5/2","2/2", "3/3", "Свободный", "6/1", "4/2", "3/2", "4/3", "4/4", "1/3", "2/1", "1/2"]

    buttons = []
    for option in schedule_options:
        if option in current_schedule:
            text = f"✅ {option}"
        else:
            text = f"➕ {option}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"sсhedule_toggle_{option}")])
    
    buttons.append([InlineKeyboardButton(text="💾 Сохранить", callback_data="schedule_save")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="schedule_cancel")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.delete()
    await callback.message.answer("Выберите график работы (можно несколько):", reply_markup=keyboard)

    await callback.answer()
    await state.set_state(FilterForm.choosing_shedule)



class FilterForm(StatesGroup):
    city = State()
    salary = State()
    specialization = State()
    payday = State()
    experience = State()
    employmentZan = State()
    schedule = State()
    work_hours = State()
    work_format = State()
    newest_first = State()
    employment_type = State()
    waiting_for_input = State()
    choosing_shedule = State()
    


@router.message(Command("set_filters"))
async def set_filters(message: Message, state: FSMContext):
    await message.answer("Напишите город")
    await state.set_state(FilterForm.city)

@router.message(FilterForm.city)
async def get_city(message: Message, state: FSMContext):
    city = message.text
    await state.update_data(city=city)
    await message.answer("Теперь введите желаемую ЗП\n" \
    "в формате мин-макс\n" \
    "или только минимальную")
    await state.set_state(FilterForm.salary)

@router.message(FilterForm.salary)
async def get_salary_range(message: Message, state: FSMContext):
    
    text = message.text.strip()
    salary_from = None
    salary_to = None
    # Проверка на дефис
    if '-' in text:
        parts = text.split('-')
        if len(parts) == 2:
            left = parts[0].strip()
            right = parts[1].strip()
            try:
                salary_from = normalize_number(left)
                salary_to = normalize_number(right)
            except ValueError:
                await message.answer("Ошибка: введите числа (цифры), можно с пробелами или запятыми, например: 7 000 - 10 000")
                return
        else:
            await message.answer("Ошибка: используйте один дефис для диапазона, например: 70000-150000 или 70 000 - 150 000")
            return
    else:
        # Одно число – минимальная зарплата
        try:
            salary_from = normalize_number(text)
        except ValueError:
            await message.answer("Ошибка: нужно ввести число (только цифры, можно с пробелами или запятыми)")
            logger.info(
            "Incorrect Input",
            user_id = message.from_user.id,
            username=message.from_user.username,
            message=message.text,
            command = "/set_filters"
            )
            return

    await state.update_data(salary_from=salary_from, salary_to=salary_to)



    await state.set_state(FilterForm.specialization)
    await message.answer("Напишите свою специализацию")


def get_filters_keyboard(data: dict) -> InlineKeyboardMarkup:
    city = data.get('city', 'не задан')
    salary_from = data.get('salary_from')
    salary_to = data.get('salary_to')
    if salary_from or salary_to:
        salary_text = f"{salary_from or '…'} – {salary_to or '…'}"
    else:
        salary_text = "не задана"
    
    schedule_val = data.get('schedule')
    if schedule_val and isinstance(schedule_val, list):
        schedule_text = ", ".join(schedule_val) if schedule_val else "не задан"
    else:
        schedule_text = "не задан"


    specialization = data.get('specialization', 'не задана')
    experience = data.get('experience', 'не задан')
    work_format = data.get('work_format', 'не задан')
    keywords = ', '.join(data.get('find_key_words', [])) or 'не заданы'
    exclude = ', '.join(data.get('exclude_key_words', [])) or 'не заданы'

    buttons = [
        [InlineKeyboardButton(text=f"🏙 Город: {city}", callback_data="edit_city")],
        [InlineKeyboardButton(text=f"💰 Зарплата: {salary_text}", callback_data="edit_salary")],
        [InlineKeyboardButton(text=f"🧠 Специализация: {specialization}", callback_data="edit_specialization")],
        [InlineKeyboardButton(text=f"🕒 Опыт: {experience}", callback_data="edit_experience")],
        [InlineKeyboardButton(text=f"📅 График: {schedule_text}", callback_data="edit_schedule")],
        [InlineKeyboardButton(text=f"🏢 Формат работы: {work_format}", callback_data="edit_work_format")],
        [InlineKeyboardButton(text=f"🔑 Ключевые слова: {keywords}", callback_data="edit_keywords")],
        [InlineKeyboardButton(text=f"❌ Исключаемые слова: {exclude}", callback_data="edit_exclude")],
        [InlineKeyboardButton(text="✅ Готово", callback_data="close_filters")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(lambda c: c.data == "close_filters")
async def close_and_save_filters(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    state_data = await state.get_data()
    new_filters = state_data.get("filters", {})
    tg_id = callback.from_user.id
    await save_filters(session, new_filters, tg_id)

    await callback.message.delete()






@router.message(Command("show_filters"))
async def show_filters(message: Message, state: FSMContext, session: AsyncSession):
    tg_id = message.from_user.id
    # Получаем словарь с фильтрами (если нет — пустой)
    filters_dict = await get_user_filters(session, tg_id)
    
    # Сохраняем фильтры в состояние (если нужно для следующих шагов редактирования)
    await state.update_data(filters=filters_dict)
    await state.set_state(FilterForm.waiting_for_input)
    
    # Генерируем клавиатуру
    keyboard = get_filters_keyboard(filters_dict)
    await message.answer("🔍 Настройки фильтрации:", reply_markup=keyboard)









@router.callback_query(lambda c: c.data.startswith("sсhedule_toggle_"))
async def schedule_toggle(callback: CallbackQuery, state: FSMContext):
    option = callback.data.split("_", 2)[2]  
    data = await state.get_data()
    filters = data.get("filters", {})
    current = filters.get("schedule", [])
    
    if option in current:
        current.remove(option)   
    else:
        current.append(option)   
    
    filters["schedule"] = current
    await state.update_data(filters=filters)
    await show_shedule_choise(callback, state)


@router.callback_query(lambda c: c.data == "schedule_save")
async def schedule_save(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    filters = data.get("filters", {})
    # Сохранять в БД пока не нужно, просто возвращаемся в главное меню
    await state.update_data(filters=filters, awaiting_field=None)
    # Показываем обновлённое главное меню
    keyboard = get_filters_keyboard(filters)
    await callback.message.delete()
    await callback.message.answer("🔍 Настройки фильтрации:", reply_markup=keyboard)
    await state.set_state(FilterForm.waiting_for_input)  # или None
    await callback.answer()

@router.callback_query(lambda c: c.data == "schedule_cancel")
async def schedule_cancel(callback: CallbackQuery, state: FSMContext):
    # Возврат без сохранения изменений
    data = await state.get_data()
    filters = data.get("filters", {})
    keyboard = get_filters_keyboard(filters)
    await callback.message.delete()
    await callback.message.answer("🔍 Настройки фильтрации:", reply_markup=keyboard)
    await state.set_state(FilterForm.waiting_for_input)
    await callback.answer()





@router.callback_query(lambda c: c.data.startswith("edit_schedule"))
async def start_shedule_changing(callback: CallbackQuery, state: FSMContext):
    await show_shedule_choise(callback, state)



    # сохранение данных в БД

    # await state.clear()
    # # Форматируем числа с запятыми как разделитель тысяч
    # from_fmt = f"{salary_from:,}" if salary_from is not None else "не указано"
    # if salary_to:
    #     to_fmt = f"{salary_to:,}"
    #     await message.answer("Фильтр Сохранён успешно\n" \
    #                         f"Город: {city}\n" \
    #                         f"Зарплата: {from_fmt} - {to_fmt}")
    #     logger.info(
    #     "salary_w_max",
    #     user_id = message.from_user.id,
    #     username=message.from_user.username,
    #     command = "/set_filters"
    #     )                   
    # else:
    #     await message.answer("Фильтр Сохранён успешно\n" \
    #                         f"Город: {city}\n" \
    #                         f"Зарплата: {from_fmt}")
    #     logger.info(
    #     "salary_w_only_min",
    #     user_id = message.from_user.id,
    #     username=message.from_user.username,
    #     command = "/set_filters"
    #     )      