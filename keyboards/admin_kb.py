from sqlalchemy import BigInteger, ForeignKey, String, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import List

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20), default="client")
    language: Mapped[str] = mapped_column(String(5), default="ru")
    
    packages: Mapped[List["Package"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class Package(Base):
    __tablename__ = 'packages'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    package_type: Mapped[str] = mapped_column(String(20)) # massage / education
    total_sessions: Mapped[int] = mapped_column()
    used_sessions: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(20), default="active") # active / completed
    
    user: Mapped["User"] = relationship(back_populates="packages")

class History(Base):
    __tablename__ = 'history'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    action_type: Mapped[str] = mapped_column(String(20))
    amount: Mapped[int] = mapped_column()
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=func.now())
