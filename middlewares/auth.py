from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser

from database.requests import get_user_by_tg_id

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # 🛡 PRO-TRICK: Безопасное извлечение Telegram ID.
        # aiogram 3 сам находит юзера в любом типе апдейта и кладет его сюда.
        tg_user: TgUser | None = data.get("event_from_user")
        
        if tg_user:
            # Ищем юзера в базе. Если он в архиве или его нет — вернет None
            db_user = await get_user_by_tg_id(tg_user.id)
            data["db_user"] = db_user
        else:
            # На случай системных апдейтов без юзера
            data["db_user"] = None
            
        return await handler(event, data)
