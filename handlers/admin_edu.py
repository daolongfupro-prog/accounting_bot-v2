from __future__ import annotations

import logging

from aiogram import Bot, F, Router
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
from handlers.admin_massage import IsAdmin
from keyboards.admin_kb import get_edu_admin_kb

logger = logging.getLogger(__name__)
router = Router()

PACKAGE_OPTIONS = [4, 8, 12]


class AddStudentForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_package = State()


def _package_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *[
                [InlineKeyboardButton(
                    text=f"{n} занятий",
                    callback_data=f"edu_pkg_{n}",
                )]
                for n in PACKAGE_OPTIONS
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_edu")],
        ]
    )


def _back_to_edu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 В меню обучения", callback_data="admin_edu")],
    ])


@router.callback_query(IsAdmin(), F.data == "admin_edu")
async def edu_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "🎓 <b>Управление обучением</b>",
        reply_markup=get_edu_admin_kb(),
    )


@router.callback_query(IsAdmin(), F.data == "edu_add_student")
async def add_student_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "📝 Введите ФИО ученика:",
        reply_markup=_back_to_edu_kb(),
    )
    await state.set_state(AddStudentForm.waiting_for_name)


@router.message(IsAdmin(), AddStudentForm.waiting_for_name)
async def add_student_name(message: Message, state: FSMContext) -> None:
    n
