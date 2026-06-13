from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from bot.states.filter_states import FilterForm
from bot.keyboard.filter_keyboard import get_filters_keyboard 

city_router = Router(name="city_widget")


async def show_city_filter_dialog(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    filters = data.get("filters", {})
    cities = filters.get("city", [])   

    buttons = []
    # Кнопки уже добавленных городов 
    for city in cities:
        buttons.append([InlineKeyboardButton(text=f"❌ {city}", callback_data=f"remove_city_{city}")])
    # Кнопка добавления нового города
    buttons.append([InlineKeyboardButton(text="➕ Добавить город", callback_data="add_city")])
    # Кнопка возврата в главное меню
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="city_back")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("Управление городами:", reply_markup=keyboard)
    await callback.answer()


@city_router.callback_query(lambda c: c.data == "add_city")
async def add_city_start(callback: CallbackQuery, state: FSMContext):
    # Сохраняем в state, что ожидаем ввод города
    await state.update_data(expecting="city")
    # Переключаем состояние на ожидание текстового ввода
    await state.set_state(FilterForm.waiting_for_input)
    # Отвечаем на callback и просим написать город
    await callback.answer()
    await callback.message.answer("Напишите название города (например, Москва)")


@city_router.callback_query(lambda c: c.data == "city_back")
async def city_back(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    filters = data.get("filters", {})
    keyboard = get_filters_keyboard(filters)
    await callback.message.edit_text("🔍 Настройки фильтрации:", reply_markup=keyboard)
    await state.set_state(FilterForm.waiting_for_input)
    await callback.answer()


@city_router.callback_query(lambda c: c.data.startswith("remove_city_"))
async def remove_city(callback: CallbackQuery, state: FSMContext):
    city_to_remove = callback.data.split("_", 2)[2] 
    data = await state.get_data()
    filters = data.get("filters", {})
    cities = filters.get("city", [])
    if city_to_remove in cities:
        cities.remove(city_to_remove)
    filters["city"] = cities
    await state.update_data(filters=filters)
    # Перерисовываем меню городов
    await show_city_filter_dialog(callback, state)

