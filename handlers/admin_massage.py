from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import settings
# Твои импорты из базы (оставил как в твоем примере)
from database.models import PackageStatus, PackageType
from database.requests import (
    create_client_with_package,
    deduct_sessions,
    get_active_users_by_type,
)
from keyboards.admin_kb import get_massage_admin_kb

logger = logging.getLogger(__name__)
router = Router()

PACKAGE_OPTIONS = [5, 10, 15]

# Фильтр проверки на админа
class IsAdmin(Filter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return event.from_user.id in settings.SUPERADMIN_IDS

# Применяем фильтр ко ВСЕМУ роутеру сразу, чтобы не писать в каждом хэндлере
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

# Наши состояния
class AddClientForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_package = State()

# Создаем клавиатуру с выбором пакетов
def _package_kb() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=f"{pkg} сеансов", callback_data=f"pkg_{pkg}")]
        for pkg in PACKAGE_OPTIONS
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- ШАГ 1: Запуск добавления клиента ---
# Замени "Добавить клиента" на текст твоей кнопки или команду
@router.message(F.text == "Добавить клиента") 
async def start_add_client(message: Message, state: FSMContext):
    await message.answer("Введите имя нового клиента:")
    await state.set_state(AddClientForm.waiting_for_name)


# --- ШАГ 2: Получаем имя и спрашиваем пакет ---
# Важно: ловим именно текстовое сообщение в состоянии waiting_for_name
@router.message(AddClientForm.waiting_for_name, F.text)
async def process_name(message: Message, state: FSMContext):
    # Сохраняем имя в память FSM
    await state.update_data(client_name=message.text)
    
    await message.answer(
        f"Имя '{message.text}' сохранено. Выберите количество сеансов:",
        reply_markup=_package_kb()
    )
    # Переводим на ожидание нажатия кнопки
    await state.set_state(AddClientForm.waiting_for_package)


# --- ШАГ 3: Ловим нажатие кнопки с пакетом ---
# ОЧЕНЬ ВАЖНО: Здесь должен быть router.callback_query, а не router.message!
@router.callback_query(AddClientForm.waiting_for_package, F.data.startswith("pkg_"))
async def process_package(call: CallbackQuery, state: FSMContext):
    # Достаем количество сеансов из callback_data (например, из "pkg_10" достаем "10")
    sessions_count = int(call.data.split("_")[1])
    
    # Достаем сохраненное имя клиента
    user_data = await state.get_data()
    client_name = user_data.get("client_name")
    
    # --- ТУТ ТВОЯ ЛОГИКА БАЗЫ ДАННЫХ ---
    # Например:
    # await create_client_with_package(name=client_name, sessions=sessions_count, ...)
    
    # Отвечаем админу и редактируем сообщение с кнопками
    await call.message.edit_text(
        f"✅ Клиент <b>{client_name}</b> успешно добавлен!\n"
        f"Оплачено сеансов: {sessions_count}",
        parse_mode="HTML"
    )
    
    # Завершаем диалог и очищаем FSM
    await state.clear()
    
    # Уведомляем Telegram, что колбек обработан (чтобы часики на кнопке не висели)
    await call.answer()
