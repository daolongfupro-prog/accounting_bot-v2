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
from aiogram.utils.deep_linking import create_start_link

from config import settings
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

# Применяем фильтр админа ко всему роутеру, чтобы защитить все функции
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


class AddClientForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_package = State()


def _package_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *[
                [InlineKeyboardButton(
                    text=f"{n} сеансов",
                    callback_data=f"msg_pkg_{n}",
                )]
                for n in PACKAGE_OPTIONS
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_massage")],
        ]
    )


def _back_to_massage_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 В меню массажа", callback_data="admin_massage")],
    ])


# --- ГЛАВНОЕ МЕНЮ МАССАЖА ---
# ВАЖНО: Убедись, что кнопка "Массаж" в твоей клавиатуре выдает callback_data="admin_massage"
@router.callback_query(F.data == "admin_massage")
async def massage_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        "💆‍♀️ <b>Управление массажем</b>",
        reply_markup=get_massage_admin_kb(),
    )


# --- ШАГ 1: Старт добавления клиента ---
# ВАЖНО: Убедись, что кнопка "Добавить клиента" выдает callback_data="massage_add_client"
@router.callback_query(F.data == "massage_add_client")
async def add_client_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "📝 Введите имя нового клиента на массаж:",
        reply_markup=_back_to_massage_kb(),
    )
    await state.set_state(AddClientForm.waiting_for_name)


# --- ШАГ 2: Получаем имя (текстовое сообщение) ---
@router.message(AddClientForm.waiting_for_name, F.text)
async def add_client_name(message: Message, state: FSMContext) -> None:
    await state.update_data(client_name=message.text)
    await message.answer(
        f"Имя '{message.text}' принято.\nВыберите количество сеансов:",
        reply_markup=_package_kb(),
    )
    await state.set_state(AddClientForm.waiting_for_package)


# --- ШАГ 3: Выбор пакета, сохранение в БД и выдача ссылки ---
@router.callback_query(AddClientForm.waiting_for_package, F.data.startswith("msg_pkg_"))
async def add_client_package(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    sessions_count = int(callback.data.split("_")[2])
    user_data = await state.get_data()
    client_name = user_data.get("client_name")
    
    # 1. Сохраняем в базу данных. 
    # Предполагается, что твоя функция возвращает созданного клиента (чтобы мы могли взять его ID)
    client_db_result = await create_client_with_package(
        name=client_name,
        # Если в модели требуется передать тип пакета:
        # type=PackageType.MASSAGE, 
        sessions=sessions_count
    )
    
    # Пытаемся получить ID (если функция возвращает объект алхимии, берем .id. Если просто число - берем его)
    client_id = client_db_result.id if hasattr(client_db_result, 'id') else client_db_result
    
    # 2. Генерируем уникальную ссылку-приглашение для бота
    # Бот запакует payload (например, "msg_123") в ссылку. 
    invite_payload = f"msg_{client_id}"
    invite_link = await create_start_link(bot, invite_payload, encode=True)
    
    # 3. Выдаем ссылку администратору
    await callback.message.edit_text(
        f"✅ Клиент <b>{client_name}</b> успешно добавлен!\n"
        f"Оплачено сеансов: {sessions_count}\n\n"
        f"🔗 <b>Перешлите эту ссылку клиенту для входа:</b>\n"
        f"<code>{invite_link}</code>",
        parse_mode="HTML",
        reply_markup=_back_to_massage_kb()
    )
    
    await state.clear()
    await callback.answer()
