from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from typing import List

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func
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


class ActionType(str, PyEnum):
    SESSION_USED = "session_used"
    PACKAGE_ADDED = "package_added"
    PACKAGE_COMPLETED = "package_completed"


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.CLIENT)
    language: Mapped[str] = mapped_column(String(5), default="ru")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    packages: Mapped[List[Package]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    history: Mapped[List[History]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} tg={self.telegram_id} role={self.role}>"


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

    @property
    def remaining_sessions(self) -> int:
        return self.total_sessions - self.used_sessions

    def __repr__(self) -> str:
        return f"<Package id={self.id} type={self.package_type} {self.used_sessions}/{self.total_sessions}>"


class History(Base):
    __tablename__ = "history"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action_type: Mapped[ActionType] = mapped_column(SAEnum(ActionType), nullable=False)
    amount: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="history")

    def __repr__(self) -> str:
        return f"<History id={self.id} user={self.user_id} action={self.action_type}>"


# Индексы для быстрых запросов
Index("ix_users_telegram_id", User.telegram_id)
Index("ix_packages_user_id", Package.user_id)
Index("ix_packages_status", Package.status)
Index("ix_history_user_id", History.user_id)
Index("ix_history_created_at", History.created_at)
