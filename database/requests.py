from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from database.engine import get_session
from database.models import (
    ActionType,
    History,
    Package,
    PackageStatus,
    PackageType,
    User,
    UserRole,
)

logger = logging.getLogger(__name__)


async def create_client_with_package(
    full_name: str,
    package_type: PackageType,
    total_sessions: int,
) -> int:
    role = UserRole.CLIENT if package_type == PackageType.MASSAGE else UserRole.CLIENT
    async with get_session() as session:
        user = User(full_name=full_name, role=role)
        session.add(user)
        await session.flush()

        package = Package(
            user_id=user.id,
            package_type=package_type,
            total_sessions=total_sessions,
        )
        session.add(package)
        logger.info("Создан пользователь id=%s с пакетом %s", user.id, package_type)
        return user.id


async def link_telegram_id(db_user_id: int, telegram_id: int) -> Optional[User]:
    async with get_session() as session:
        user = await session.get(User, db_user_id)
        if not user:
            logger.warning("Пользователь id=%s не найден", db_user_id)
            return None
        user.telegram_id = telegram_id
        logger.info("Привязан telegram_id=%s к user_id=%s", telegram_id, db_user_id)
        return user


async def get_user_by_tg_id(telegram_id: int) -> Optional[User]:
    async with get_session() as session:
        result = await session.execute(
            select(User)
            .options(
                selectinload(User.packages),
                selectinload(User.history),
            )
            .where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()


async def update_user_language(telegram_id: int, lang_code: str) -> None:
    async with get_session() as session:
        await session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(language=lang_code)
        )
        logger.info("Язык пользователя tg=%s → %s", telegram_id, lang_code)


async def get_active_users_by_type(package_type: PackageType) -> list[User]:
    async with get_session() as session:
        result = await session.execute(
            select(User)
            .join(Package)
            .options(selectinload(User.packages))
            .where(
                Package.package_type == package_type,
                Package.status == PackageStatus.ACTIVE,
            )
        )
        return list(result.scalars().unique().all())


async def deduct_sessions(
    user_id: int,
    package_type: PackageType,
    amount: int,
) -> dict:
    async with get_session() as session:
        result = await session.execute(
            select(Package).where(
                Package.user_id == user_id,
                Package.package_type == package_type,
                Package.status == PackageStatus.ACTIVE,
            )
        )
        package = result.scalar_one_or_none()

        if not package:
            logger.warning("Активный пакет не найден user_id=%s type=%s", user_id, package_type)
            return {"status": "error", "message": "Пакет не найден"}

        package.used_sessions += amount

        is_completed = package.used_sessions >= package.total_sessions
        if is_completed:
            package.status = PackageStatus.COMPLETED
            action = ActionType.PACKAGE_COMPLETED
        else:
            action = ActionType.SESSION_USED

        session.add(History(user_id=user_id, action_type=action, amount=amount))

        remaining = max(0, package.total_sessions - package.used_sessions)
        logger.info("user_id=%s списано %s сессий, остаток=%s", user_id, amount, remaining)

        return {
            "status": "success",
            "remaining": remaining,
            "completed": is_completed,
        }


async def get_all_data_for_export() -> list[User]:
    async with get_session() as session:
        result = await session.execute(
            select(User).options(
                selectinload(User.packages),
                selectinload(User.history),
            )
        )
        return list(result.scalars().unique().all())
