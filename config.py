from __future__ import annotations

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Бот
    BOT_TOKEN: str = Field(..., min_length=10)

    # База данных
    DATABASE_URL: str = Field(..., min_length=10)

    # Режим отладки
    DEBUG: bool = False

    # Права доступа
    SUPERADMIN_IDS: list[int] = Field(default=[2103579364, 146156901])
    ADMIN_IDS: list[int] = Field(default=[])

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_database_url(cls, v: str) -> str:
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @property
    def all_admin_ids(self) -> list[int]:
        """Все администраторы включая супер-админов"""
        return list(set(self.SUPERADMIN_IDS + self.ADMIN_IDS))


settings = Settings()
