# bot/services/city_mapper.py
import aiohttp
from typing import Dict, List, Optional

class CityMapper:
    _city_map: Dict[str, str] = {}  
    _aliases: Dict[str, str] = {    
        "питер": "Санкт-Петербург",
        "спб": "Санкт-Петербург",
        "мск": "Москва",
        "нск": "Новосибирск",
        "екб": "Екатеринбург",
        "нн": "Нижний Новгород",
        "кз": "Казань",
        "чел": "Челябинск",
        "омск": "Омск",
        "самара": "Самара",
        "рнд": "Ростов-на-Дону",
        "уфа": "Уфа",
        "крд": "Краснодар",
        "крс": "Красноярск",
        "врн": "Воронеж",
        "пнз": "Пенза",
        "пермь": "Пермь",
        "влг": "Волгоград",
        "срт": "Саратов",
        "тлт": "Тольятти",
        "тмн": "Тюмень",
        "иж": "Ижевск",
        "брн": "Барнаул",
        "у-у": "Улан-Удэ",
        "ирк": "Иркутск",
        "влд": "Владивосток",
        "хбр": "Хабаровск",
        "якутск": "Якутск",
        "махачкала": "Махачкала",
        "сев": "Севастополь",
        "сим": "Симферополь",
        "клд": "Калининград"
    }

    @classmethod
    async def load_cities(cls):
        """Загружает справочник городов с hh.ru и заполняет _city_map."""
        url = "https://api.hh.ru/areas"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                cls._city_map = {}
                cls._recursive_parse(data)

    @classmethod
    def _recursive_parse(cls, areas):
        for area in areas:
            if area.get('areas'):
                cls._recursive_parse(area['areas'])
            else:
                # Это город (у него нет вложенных областей)
                name = area['name']
                cls._city_map[name.lower()] = name  # нормализованное имя -> оригинальное

    @classmethod
    def search_cities(cls, query: str, limit: int = 10) -> List[str]:
        """
        Ищет города, соответствующие запросу.
        Возвращает список названий (оригинальных) максимум limit штук.
        """
        query = query.lower().strip()
        if not query:
            return []

        # Проверяет синонимы
        if query in cls._aliases:
            canonical = cls._aliases[query]
            return [canonical] if canonical.lower() in cls._city_map else []

        # Ищет частичные совпадения
        results = []
        for city_lower, city_name in cls._city_map.items():
            if query in city_lower:
                results.append(city_name)
            if len(results) >= limit:
                break
        return results

    @classmethod
    def get_city_id(cls, city_name: str) -> Optional[str]:
        """Возвращает ID города по его названию (для API hh.ru)."""
        # Поиск в _city_map по ключу
        city_lower = city_name.lower()
        return cls._city_map.get(city_lower)