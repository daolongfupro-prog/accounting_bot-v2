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

# Устанавливаем фильтр IsAdmin на весь роутер, чтобы не дублировать его
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

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


# --- ГЛАВНОЕ МЕНЮ ОБУЧЕНИЯ (С ОЧИСТКОЙ СОСТОЯНИЯ!) ---
@router.callback_query(F.data == "admin_edu")
async def edu_menu(callback: CallbackQuery, state: FSMContext) -> None:
    # ОЧЕНЬ ВАЖНО: Если админ нажал "Назад" или "Отмена", мы сбрасываем FSM!
    await state.clear() 
    await callback.answer()
    await callback.message.edit_text(
        "🎓 <b>Управление обучением</b>",
        reply_markup=get_edu_admin_kb(),
    )


# --- ШАГ 1: Старт добавления ученика ---
@router.callback_query(F.data == "edu_add_student")
async def add_student_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "📝 Введите ФИО ученика:",
        reply_markup=_back_to_edu_kb(),
    )
    await state.set_state(AddStudentForm.waiting_for_name)


# --- ШАГ 2: Получаем ФИО (текст) ---
@router.message(AddStudentForm.waiting_for_name, F.text)
async def add_student_name(message: Message, state: FSMContext) -> None:
    # Сохраняем имя ученика в хранилище состояний
    await state.update_data(student_name=message.text)
    
    await message.answer(
        f"ФИО '{message.text}' принято.\nВыберите пакет занятий:",
        reply_markup=_package_kb(),
    )
    # Переводим в ожидание нажатия кнопки пакета
    await state.set_state(AddStudentForm.waiting_for_package)


# --- ШАГ 3: Получаем пакет занятий (Инлайн-кнопка) ---
@router.callback_query(AddStudentForm.waiting_for_package, F.data.startswith("edu_pkg_"))
async def add_student_package(callback: CallbackQuery, state: FSMContext) -> None:
    # Извлекаем количество занятий из колбека (например, из "edu_pkg_8" берем "8")
    sessions_count = int(callback.data.split("_")[2])
    
    # Достаем сохраненное ФИО
    user_data = await state.get_data()
    student_name = user_data.get("student_name")
    
    # ==========================================
    # ТУТ ТВОЯ ЛОГИКА БАЗЫ ДАННЫХ
    # Например:
    # await create_client_with_package(name=student_name, type=PackageType.EDU, sessions=sessions_count...)
    # ==========================================
    
    await callback.message.edit_text(
        f"✅ Ученик <b>{student_name}</b> успешно добавлен!\n"
        f"Оплачено занятий: {sessions_count}",
        parse_mode="HTML",
        reply_markup=_back_to_edu_kb() # Кнопка для возврата в меню
    )
    
    # Очищаем состояние после успешного добавления
    await state.clear()
    await callback.answer()
