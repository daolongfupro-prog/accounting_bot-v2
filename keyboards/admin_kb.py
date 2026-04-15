from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import User


def get_main_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💆‍♂️ Массаж", callback_data="admin_massage")],
            [InlineKeyboardButton(text="🎓 Обучение", callback_data="admin_edu")],
            [InlineKeyboardButton(text="📥 Выгрузить Excel (Бэкап)", callback_data="admin_backup")],
        ]
    )


def get_massage_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить клиента", callback_data="massage_add_client")],
            [InlineKeyboardButton(text="👥 Управление клиентами", callback_data="massage_manage_users")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")],
        ]
    )


def get_edu_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить ученика", callback_data="edu_add_student")],
            [InlineKeyboardButton(text="👥 Управление учениками", callback_data="edu_manage_users")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="edu_stats")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")],
        ]
    )


# --- ДИНАМИЧЕСКИЕ КЛАВИАТУРЫ (ВЕРСИЯ 2.0) ---

def get_users_list_kb(users: list[User], prefix: str) -> InlineKeyboardMarkup:
    """Генерирует список пользователей. prefix = 'msg' или 'edu'"""
    builder = InlineKeyboardBuilder()
    
    for user in users:
        # callback будет иметь вид, например: msg_user_15 или edu_user_42
        builder.button(text=user.full_name, callback_data=f"{prefix}_user_{user.id}")
    
    # Кнопка возврата в нужное меню
    back_data = "admin_massage" if prefix == "msg" else "admin_edu"
    builder.button(text="🔙 Назад", callback_data=back_data)
    
    builder.adjust(1)  # Выстраиваем кнопки в один столбец
    return builder.as_markup()


def get_user_manage_kb(user_id: int, prefix: str) -> InlineKeyboardMarkup:
    """Клавиатура внутри карточки конкретного клиента"""
    manage_back = "massage_manage_users" if prefix == "msg" else "edu_manage_users"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📉 Списать", callback_data=f"{prefix}_deduct_{user_id}")],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"{prefix}_delete_{user_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=manage_back)],
        ]
    )


def get_deduction_time_kb(user_id: int, prefix: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора времени при списании"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏱ Списать текущим временем", callback_data=f"{prefix}_time_now_{user_id}")],
            [InlineKeyboardButton(text="📅 Ввести дату/время вручную", callback_data=f"{prefix}_time_custom_{user_id}")],
            [InlineKeyboardButton(text="🔙 Отмена", callback_data=f"{prefix}_user_{user_id}")],
        ]
    )


def get_confirm_delete_kb(user_id: int, prefix: str) -> InlineKeyboardMarkup:
    """Защита от случайного удаления (Архивация)"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚨 ДА, УДАЛИТЬ", callback_data=f"{prefix}_confirm_del_{user_id}")],
            [InlineKeyboardButton(text="🔙 ОТМЕНА", callback_data=f"{prefix}_user_{user_id}")],
        ]
    )
