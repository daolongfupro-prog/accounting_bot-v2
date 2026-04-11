from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_admin_kb() -> InlineKeyboardMarkup:
    """Главное меню администратора"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💆‍♀️ Управление Массажем", callback_data="admin_massage")],
        [InlineKeyboardButton(text="🎓 Управление Обучением", callback_data="admin_edu")],
        [InlineKeyboardButton(text="👥 Список Администраторов", callback_data="admin_list")]
    ])

def get_massage_admin_kb() -> InlineKeyboardMarkup:
    """Меню раздела 'Массаж'"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить клиента", callback_data="msg_add_client"),
            InlineKeyboardButton(text="➖ Списать сеанс", callback_data="msg_deduct")
        ],
        [InlineKeyboardButton(text="📊 Статистика и остатки", callback_data="msg_stats")],
        [InlineKeyboardButton(text="🔙 Назад в главное меню", callback_data="admin_main")]
    ])
