from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


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
            [InlineKeyboardButton(text="➕ Добавить клиента", callback_data="msg_add_client")],
            [InlineKeyboardButton(text="📉 Списать сеанс", callback_data="msg_deduct")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")],
        ]
    )


def get_edu_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить ученика", callback_data="edu_add_student")],
            [InlineKeyboardButton(text="📉 Списать занятие", callback_data="edu_deduct_list")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="edu_stats")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")],
        ]
    )
