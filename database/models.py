from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from typing import List

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class UserRole(str, PyEnum):
    CLIENT = "client"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class PackageType(str, PyEnum):
    MASSAGE = "massage"
    EDUCATION = "education"


class PackageStatus(str, PyEnum):
    ACTIVE = "active"
    COMPLETED = "completed"


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # telegram_id nullable=True, так как карточка создается админом до перехода по ссылке
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.CLIENT)
    language: Mapped[str] = mapped_column(String(5), default="ru")
    # Флаг для безопасного удаления (клиент скрыт, но статистика в Excel цела)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    packages: Mapped[List[Package]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    visits: Mapped[List[Visit]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} tg={self.telegram_id} role={self.role} archived={self.is_archived}>"


class Package(Base):
    __tablename__ = "packages"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    package_type: Mapped[PackageType] = mapped_column(SAEnum(PackageType), nullable=False)
    total_sessions: Mapped[int] = mapped_column(nullable=False)
    used_sessions: Mapped[int] = mapped_column(default=0)
    status: Mapped[PackageStatus] = mapped_column(
        SAEnum(PackageStatus), default=PackageStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="packages")
    visits: Mapped[List[Visit]] = relationship(
        back_populates="package", cascade="all, delete-orphan"
    )

    @property
    def remaining_sessions(self) -> int:
        return self.total_sessions - self.used_sessions

    def __repr__(self) -> str:
        return f"<Package id={self.id} type={self.package_type} {self.used_sessions}/{self.total_sessions}>"


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    package_id: Mapped[int] = mapped_column(ForeignKey("packages.id"), nullable=False)
    
    # Фактическое время визита (можно менять задним числом)
    visit_time: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    
    # Фактическое списание (-1)
    amount: Mapped[int] = mapped_column(default=-1, nullable=False)
    # Остаток после этого списания (идеально для подсчетов в Excel)
    balance_after: Mapped[int] = mapped_column(nullable=False)
    
    # Системное время (когда именно админ нажал кнопку в боте)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="visits")
    package: Mapped[Package] = relationship(back_populates="visits")

    def __repr__(self) -> str:
        return f"<Visit id={self.id} user={self.user_id} package={self.package_id} time={self.visit_time}>"


# Индексы для быстрых запросов
Index("ix_users_telegram_id", User.telegram_id)
Index("ix_users_is_archived", User.is_archived)
Index("ix_packages_user_id", Package.user_id)
Index("ix_packages_status", Package.status)
Index("ix_visits_user_id", Visit.user_id)
Index("ix_visits_package_id", Visit.package_id)
Index("ix_visits_visit_time", Visit.visit_time)
