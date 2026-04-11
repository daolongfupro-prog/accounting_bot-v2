from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from database.engine import async_session
from database.models import User, Package, History

async def create_client_with_package(full_name: str, package_type: str, total_sessions: int) -> int:
    async with async_session() as session:
        new_user = User(full_name=full_name, role="client" if package_type == "massage" else "student")
        session.add(new_user)
        await session.flush() 
        new_package = Package(user_id=new_user.id, package_type=package_type, total_sessions=total_sessions)
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
        result = await session.execute(
            select(User).options(selectinload(User.packages)).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

async def update_user_language(telegram_id: int, lang_code: str):
    async with async_session() as session:
        await session.execute(
            update(User).where(User.telegram_id == telegram_id).values(language=lang_code)
        )
        await session.commit()

async def get_active_users_by_type(package_type: str):
    async with async_session() as session:
        result = await session.execute(
            select(User).join(Package).options(selectinload(User.packages))
            .where(Package.package_type == package_type, Package.status == 'active')
        )
        return result.scalars().unique().all()

async def deduct_sessions(user_id: int, package_type: str, amount_to_deduct: int) -> dict:
    async with async_session() as session:
        result = await session.execute(
            select(Package).where(Package.user_id == user_id, Package.package_type == package_type, Package.status == 'active')
        )
        package = result.scalar_one_or_none()
        if not package: return {"status": "error", "message": "Пакет не найден"}

        package.used_sessions += amount_to_deduct
        
        history_entry = History(user_id=user_id, action_type=package_type, amount=amount_to_deduct)
        session.add(history_entry)
        
        if package.used_sessions >= package.total_sessions:
            package.status = "completed"
        
        await session.commit()
        return {"status": "success", "remaining": max(0, package.total_sessions - package.used_sessions), "completed": package.status == "completed"}

async def get_all_data_for_export():
    async with async_session() as session:
        result = await session.execute(select(User).options(selectinload(User.packages)))
        return result.scalars().unique().all()
