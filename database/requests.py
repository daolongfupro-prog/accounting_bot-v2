async def get_active_users_by_type(package_type: PackageType) -> list[User]:
    async with get_session() as session:
        result = await session.execute(
            select(User)
            .join(Package)
            .options(
                selectinload(User.packages),
                selectinload(User.visits) # <-- ВОТ ЭТА СТРОКА ОЖИВИТ КНОПКУ
            )
            .where(
                User.is_archived == False, 
                Package.package_type == package_type,
                Package.status == PackageStatus.ACTIVE,
            )
        )
        return list(result.scalars().unique().all())
