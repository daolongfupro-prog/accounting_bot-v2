from __future__ import annotations

import logging
from datetime import datetime

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
    archive_user,
    create_client_with_package,
    deduct_sessions,
    get_active_users_by_type,
)
from keyboards.admin_kb import (
    get_confirm_delete_kb,
    get_deduction_time_kb,
    get_massage_admin_kb,
    get_user_manage_kb,
    get_users_list_kb,
)

logger = logging.getLogger(__name__)
router = Router()

PACKAGE_OPTIONS = [5, 10, 15]


class IsAdmin(Filter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return event.from_user.id in settings.SUPERADMIN_IDS


router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# --- FSM (Состояния) ---
class AddClientForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_package = State()

class CustomTimeForm(StatesGroup):
    waiting_for_time = State()


# --- ВСПОМОГАТЕЛЬНЫЕ КЛАВИАТУРЫ ---
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


# ==========================================
# 1. ГЛАВНОЕ МЕНЮ МАССАЖА
# ==========================================
@router.callback_query(F.data == "admin_massage")
async def massage_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        "💆‍♀️ <b>Управление массажем</b>",
        reply_markup=get_massage_admin_kb(),
    )


# ==========================================
# 2. ДОБАВЛЕНИЕ КЛИЕНТА
# ==========================================
@router.callback_query(F.data == "massage_add_client")
async def add_client_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "📝 Введите имя нового клиента на массаж:",
        reply_markup=_back_to_massage_kb(),
    )
    await state.set_state(AddClientForm.waiting_for_name)


@router.message(AddClientForm.waiting_for_name, F.text)
async def add_client_name(message: Message, state: FSMContext) -> None:
    await state.update_data(client_name=message.text.strip())
    await message.answer(
        f"Имя <b>{message.text}</b> принято.\nВыберите количество сеансов:",
        reply_markup=_package_kb(),
    )
    await state.set_state(AddClientForm.waiting_for_package)


@router.callback_query(AddClientForm.waiting_for_package, F.data.startswith("msg_pkg_"))
async def add_client_package(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
) -> None:
    await callback.answer()
    sessions_count = int(callback.data.split("_")[2])
    user_
