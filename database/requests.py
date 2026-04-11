from sqlalchemy import select
from database.engine import async_session
from database.models import User, Package

async def create_client_with_package(full_name: str, package_type: str, total_sessions: int) -> int:
    """Создает пользователя и сразу выдает ему пакет. Возвращает ID пользователя в базе."""
    async with async_session() as session:
        # 1. Создаем пользователя
        new_user = User(full_name=full_name, role="client" if package_type == "massage" else "student")
        session.add(new_user)
        await session.flush() # Отправляем в базу, чтобы получить сгенерированный ID
        
        # 2. Создаем пакет
        new_package = Package(
            user_id=new_user.id,
            package_type=package_type,
            total_sessions=total_sessions
        )
        session.add(new_package)
        
        # 3. Сохраняем всё окончательно
        await session.commit()
        
        return new_user.id

async def link_telegram_id(db_user_id: int, telegram_id: int) -> User:
    """Привязывает Telegram ID к карточке клиента по его секретному ID из ссылки"""
    async with async_session() as session:
        # Ищем пользователя по ID из базы
        user = await session.get(User, db_user_id)
        if user:
            # Если нашли, записываем его telegram_id
            user.telegram_id = telegram_id
            await session.commit()
            return user
        return None

async def get_user_by_tg_id(telegram_id: int) -> User:
    """Ищет пользователя по его Telegram ID (для проверки при старте)"""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()
