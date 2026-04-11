from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💆‍♂️ Массаж", callback_data="admin_massage")],
        [InlineKeyboardButton(text="🎓 Обучение", callback_data="admin_edu")],
        [InlineKeyboardButton(text="📥 Выгрузить Excel (Бэкап)", callback_data="admin_backup")]
    ])

def get_massage_admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить клиента", callback_data="msg_add_client")],
        [InlineKeyboardButton(text="📉 Списать сеанс", callback_data="msg_deduct")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")]
    ])

def get_edu_admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить ученика", callback_data="edu_add_student")],
        [InlineKeyboardButton(text="📉 Списать занятие", callback_data="edu_deduct_list")], # Изменила колбэк для ясности
        [InlineKeyboardButton(text="📊 Статистика", callback_data="edu_stats")], # ВОТ ОНА!
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main")]
    ])
