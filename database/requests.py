from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from database.engine import async_session
from database.models import User, Package

async def create_client_with_package(full_name: str, package_type: str, total_sessions: int) -> int:
    async with async_session() as session:
        new_user = User(full_name=full_name, role="client" if package_type == "massage" else "student")
        session.add(new_user)
        await session.flush() 
        
        new_package = Package(
            user_id=new_user.id,
            package_type=package_type,
            total_sessions=total_sessions
        )
        session.add(new_package)
        await session.commit()
        return new_user.id

async def link_telegram_id(db_user_id: int, telegram_id: int) -> User:
    async with async_session() as session:
        user = await session.get(User, db_user_id)
        if user:
            user.telegram_id = telegram_id
            await session.commit()
            return user
        return None

async def get_user_by_tg_id(telegram_id: int) -> User:
    async with async_session() as session:
        # selectinload нужен, чтобы сразу подтянуть данные о пакетах пользователя
        result = await session.execute(
            select(User).options(selectinload(User.packages)).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

async def update_user_language(telegram_id: int, lang_code: str):
    """Обновляет язык пользователя в базе"""
    async with async_session() as session:
        await session.execute(
            update(User).where(User.telegram_id == telegram_id).values(language=lang_code)
        )
        await session.commit()

# --- НОВЫЕ ФУНКЦИИ ДЛЯ СПИСАНИЯ И СПИСКОВ ---

async def get_active_users_by_type(package_type: str):
    """Получает список пользователей, у которых есть активный пакет (массаж или обучение)"""
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .join(Package)
            .options(selectinload(User.packages))
            .where(Package.package_type == package_type, Package.status == 'active')
        )
        # Возвращаем список уникальных пользователей
        return result.scalars().unique().all()

async def deduct_sessions(user_id: int, package_type: str, amount_to_deduct: int) -> dict:
    """Списывает сеансы и возвращает информацию об остатке"""
    async with async_session() as session:
        # Ищем активный пакет пользователя
        result = await session.execute(
            select(Package)
            .where(Package.user_id == int(user_id), Package.package_type == package_type, Package.status == 'active')
        )
        package = result.scalar_one_or_none()

        if not package:
            return {"status": "error", "message": "Активный пакет не найден."}

        # Увеличиваем количество использованных сеансов
        package.used_sessions += amount_to_deduct
        remaining = package.total_sessions - package.used_sessions

        # Если сеансы закончились, меняем статус пакета
        if remaining <= 0:
            package.status = "completed"
            remaining = 0

        await session.commit()
        
        return {
            "status": "success", 
            "remaining": remaining, 
            "completed": package.status == "completed"
        }
