from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from database.models import User

logger = logging.getLogger(__name__)

TEXTS: dict[str, dict[str, str]] = {
    "ru": {
        "main_menu": "Выберите действие:",
        "balance": "📊 Мой остаток",
        "change_lang": "🌐 Сменить язык",
        "profile_head": "📋 <b>Ваши активные услуги:</b>",
        "massage": "💆‍♂️ Массаж",
        "edu": "🎓 Обучение",
        "rem": "Остаток",
        "of": "из",
        "active": "✅ Активен",
        "completed": "🏁 Завершен",
        "lang_set": "✅ Язык установлен!",
        "no_services": "У вас пока нет активных услуг.",
        "access_denied": "🔒 Доступ ограничен. Обратитесь к мастеру.",
        "invalid_link": "❌ Ссылка недействительна.",
        "welcome_back": "Рады видеть вас снова, {name}!",
        "choose_lang": "Выберите язык / Tilni tanlang / Choose language:",
        "greeting": "🌟 Здравствуйте, <b>{name}</b>!\nВыберите язык / Tilni tanlang / Choose language:",
    },
    "uz": {
        "main_menu": "Harakatni tanlang:",
        "balance": "📊 Mening qoldig'im",
        "change_lang": "🌐 Tilni o'zgartirish",
        "profile_head": "📋 <b>Sizning faol xizmatlaringiz:</b>",
        "massage": "💆‍♂️ Massaj",
        "edu": "🎓 O'qitish",
        "rem": "Qoldiq",
        "of": "dan",
        "active": "✅ Faol",
        "completed": "🏁 Yakunlandi",
        "lang_set": "✅ Til o'rnatildi!",
        "no_services": "Hozircha faol xizmatlaringiz yo'q.",
        "access_denied": "🔒 Kirish cheklangan. Ustaga murojaat qiling.",
        "invalid_link": "❌ Havola yaroqsiz.",
        "welcome_back": "Sizi yana ko'rganimizdan xursandmiz, {name}!",
        "choose_lang": "Выберите язык / Tilni tanlang / Choose language:",
        "greeting": "🌟 Xush kelibsiz, <b>{name}</b>!\nВыберите язык / Tilni tanlang / Choose language:",
    },
    "en": {
        "main_menu": "Choose an action:",
        "balance": "📊 My balance",
        "change_lang": "🌐 Change language",
        "profile_head": "📋 <b>Your active services:</b>",
        "massage": "💆‍♂️ Massage",
        "edu": "🎓 Education",
        "rem": "Remaining",
        "of": "of",
        "active": "✅ Active",
        "completed": "🏁 Completed",
        "lang_set": "✅ Language set!",
        "no_services": "You have no active services yet.",
        "access_denied": "🔒 Access denied. Please contact your master.",
        "invalid_link": "❌ Invalid link.",
        "welcome_back": "Welcome back, {name}!",
        "choose_lang": "Выберите язык / Tilni tanlang / Choose language:",
        "greeting": "🌟 Hello, <b>{name}</b>!\nВыберите язык / Tilni tanlang / Choose language:",
    },
}


def get_texts(user: User | None) -> dict[str, str]:
    """Возвращает словарь переводов по языку пользователя"""
    lang = user.language if user and user.language in TEXTS else "ru"
    return TEXTS[lang]


class I18nMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        db_user: User | None = data.get("db_user")
        data["texts"] = get_texts(db_user)
        return await handler(event, data)
