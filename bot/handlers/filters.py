from aiogram import Router, F
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
import structlog



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




class FilterForm(StatesGroup):
    city = State()
    salary = State()

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

    user_data = await state.get_data()
    city = user_data.get('city')


    user_data = await state.get_data()
    city = user_data.get('city')

    # сохранение данных в БД

    await state.clear()
    # Форматируем числа с запятыми как разделитель тысяч
    from_fmt = f"{salary_from:,}" if salary_from is not None else "не указано"
    if salary_to:
        to_fmt = f"{salary_to:,}"
        await message.answer("Фильтр Сохранён успешно\n" \
                            f"Город: {city}\n" \
                            f"Зарплата: {from_fmt} - {to_fmt}")
        logger.info(
        "salary_w_max",
        user_id = message.from_user.id,
        username=message.from_user.username,
        command = "/set_filters"
        )                   
    else:
        await message.answer("Фильтр Сохранён успешно\n" \
                            f"Город: {city}\n" \
                            f"Зарплата: {from_fmt}")
        logger.info(
        "salary_w_only_min",
        user_id = message.from_user.id,
        username=message.from_user.username,
        command = "/set_filters"
        )      