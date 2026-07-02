import asyncio
from unittest.mock import MagicMock
from aiogram.types import Message, User

# 1. Импортируем вашу реальную фабрику сессий
from bot.db.database import Async_Fabric_Session  # Замените bot.db.base на ваш реальный файл, где лежит этот код (например, bot.db.database)

# 2. Импортируем ваши функции обработки фильтров и класс API
from bot.services.to_hhApi import filters_to_params_hh_api
from bot.services.to_hhApi import HHAPI  # Укажите ваш файл с классом HHAPI

async def run_test():
    # Создаем фальшивый объект message с ID пользователя, который точно есть в БД
    mock_message = MagicMock(spec=Message)
    mock_message.from_user = MagicMock(spec=User)
    
    # 🛑 ОБЯЗАТЕЛЬНО: Поставьте сюда ваш реальный Telegram ID, у которого заполнены фильтры в БД
    mock_message.from_user.id = 7183877497  

    # Открываем вашу реальную асинхронную сессию
    async with Async_Fabric_Session() as session:
        print("1. Формируем параметры запроса из фильтров БД...")
        try:
            params = await filters_to_params_hh_api(message=mock_message, session=session)
            print(f"👉 Сформированные параметры для HH: {params}\n")
            
            print("2. Отправляем тестовый запрос в API hh.ru (в обход Happ)...")
            response = await HHAPI.search_vacancies(params)
            
            print("✨ УСПЕХ! Ответ от HeadHunter успешно получен:")
            print(f"Всего найдено вакансий по вашим фильтрам: {response.get('found', 0)}")
            
            # Показываем первые 3 вакансии для проверки вывода
            items = response.get('items', [])
            if items:
                print("\nПримеры найденных вакансий:")
                for i, vacancy in enumerate(items[:3], 1):
                    salary = vacancy.get('salary')
                    salary_str = "Не указана"
                    if salary:
                        fr = f"от {salary.get('from')}" if salary.get('from') else ""
                        to = f"до {salary.get('to')}" if salary.get('to') else ""
                        salary_str = f"{fr} {to} {salary.get('currency')}".strip()
                        
                    print(f"{i}. {vacancy.get('name')} | Зарплата: {salary_str} | Компания: {vacancy.get('employer', {}).get('name')}")
            else:
                print("⚠ Вакансий по выбранным фильтрам не обнаружено.")
                
        except Exception as e:
            print(f"❌ Произошла ошибка во время теста: {e}")

if __name__ == "__main__":
    asyncio.run(run_test())
