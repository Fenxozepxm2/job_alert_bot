from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from bot.db.models import User, Filter_HH, VacancyAction, ActionType
from datetime import datetime
from typing import Set




async def save_user(
        session: AsyncSession,
        tg_id: int,
        username: str,
        last_seen_in_bot: datetime,
        created_at: datetime,
        name: str
) -> User :
    "Запись нового юзера в БД"
    
    query = select(User).where(User.tg_id == tg_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        
        user = User(
        tg_id = tg_id,
        username = username,
        last_seen_in_bot = last_seen_in_bot,
        created_at = created_at,
        name = name,
    )
        session.add(user)
        await session.commit()
        return user
    else:
        return user
    


async def get_user(
        session: AsyncSession,
        tg_id: int,
        username: str | None = None,
) -> dict:
    "Получение юзера из БД"
    query = await session.execute(select(User).where(User.tg_id == tg_id))
    user = query.scalar_one_or_none()
    if not user:
        raise ValueError()
    return user


async def get_user_filters(
        session: AsyncSession,
        tg_id: int
) -> dict:
    query = select(Filter_HH.filters).where(Filter_HH.tg_id == tg_id)
    result = await session.execute(query)
    filters = result.scalar_one_or_none()
    return filters if filters is not None else {}





async def save_filters(
        session: AsyncSession,
        new_filters: dict,
        tg_id: int
) -> dict:
    "полностью обновить фильтры(удаляя всё, что не находится в new_filters)"
    query = select(Filter_HH).where(Filter_HH.tg_id == tg_id)
    result = await session.execute(query)
    filters_db = result.scalar_one_or_none()

    if filters_db:
        filters_db.filters = new_filters
    else:
        filters_db = Filter_HH(
            tg_id = tg_id,
            filters = new_filters
        )
        session.add(filters_db)
    
    await session.commit()
    
    return filters_db.filters




async def patch_filters(
        session: AsyncSession,
        tg_id: int,
        update_data: dict
) -> dict: 
    "Обновить частисно фильтры"
    query = select(Filter_HH).where(Filter_HH.tg_id == tg_id)
    result = await session.execute(query)
    filters_db = result.scalar_one_or_none()

    if not filters_db:
        filters_db = Filter_HH(
            tg_id = tg_id,
            filters = update_data
        )
    else:
        current_filters = dict(filters_db.filters)
        current_filters.update(update_data)
        filters_db.filters = current_filters

    await session.commit()
    return filters_db.filters





async def add_vacancy_action(
    session: AsyncSession,
    tg_id: int,
    vacancy: dict,
    action: str  # "like" или "skip"
) -> bool:
    """
    Сохраняет лайк или скип в базу данных. 
    Возвращает True в случае успеха, и False если запись уже существует.
    """
    # 1. Находим внутренний ID пользователя
    user_stmt = select(User.id).where(User.tg_id == tg_id)
    user_res = await session.execute(user_stmt)
    db_user_id = user_res.scalar_one_or_none()
    
    if not db_user_id:
        return False

    db_action = ActionType.LIKE if action == "like" else ActionType.SKIP

    try:
        new_action = VacancyAction(
            user_id=db_user_id, 
            vacancy_id=str(vacancy.get("id")),
            action=db_action,
            vacancy_title=vacancy.get("name"),
            vacancy_url=vacancy.get("alternate_url")
        )
        session.add(new_action)
        await session.commit()
        return True
        
    except Exception as e:
        await session.rollback()
        return False

    

async def get_viewed_vacancy_ids(session: AsyncSession, tg_id: int) -> Set[str]:
    """
    Возвращает множество (set) всех ID вакансий, которые пользователь уже лайкнул или скрыл.
    """
    # Сначала находим внутренний ID пользователя по его tg_id
    user_stmt = select(User.id).where(User.tg_id == tg_id)
    user_res = await session.execute(user_stmt)
    db_user_id = user_res.scalar_one_or_none()
    
    if not db_user_id:
        return set()  

    # Выбираем только поле vacancy_id для этого пользователя
    vac_id = select(VacancyAction.vacancy_id).where(VacancyAction.user_id == db_user_id)
    result = await session.execute(vac_id)
    
    # scalars().all() вернет список строк, превращаем его в set для быстрой фильтрации
    return set(result.scalars().all())

async def get_favorite_vac(session: AsyncSession, tg_id: int) -> list:
    user_tg_id = select(User.id).where(User.tg_id == tg_id)
    user_result = await session.execute(user_tg_id)

    db_user_id = user_result.scalar_one_or_none()

    if not db_user_id:
        return {}
    
    vac_action = select(VacancyAction).where(VacancyAction.user_id == db_user_id).where(VacancyAction.action == ActionType.LIKE)
    vac_act_res = await session.execute(vac_action)

    favorite_vac = vac_act_res.scalars().all()

    print(favorite_vac)

    return  favorite_vac



async def del_fav_vac_from_db(session: AsyncSession, tg_id: int, vacancy_id: str) -> bool:

    user_tg_id = select(User.id).where(User.tg_id == tg_id)
    user_result = await session.execute(user_tg_id)

    db_user_id = user_result.scalar_one_or_none()

    if not db_user_id:
        return 0
    
    delete_vac = delete(VacancyAction).where(
        VacancyAction.user_id == db_user_id,
        VacancyAction.vacancy_id == str(vacancy_id)
    )
    await session.execute(delete_vac)
    await session.commit()


