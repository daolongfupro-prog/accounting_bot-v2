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
    get_edu_admin_kb,
    get_user_manage_kb,
    get_users_list_kb,
)

logger = logging.getLogger(__name__)
router = Router()

PACKAGE_OPTIONS = [12, 37, 75]


class IsAdmin(Filter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return event.from_user.id in settings.SUPERADMIN_IDS


router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# --- FSM (Состояния) ---
class AddStudentForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_package = State()

class EduCustomTimeForm(StatesGroup):
    waiting_for_time = State()


# --- ВСПОМОГАТЕЛЬНЫЕ КЛАВИАТУРЫ ---
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


@router.callback_query(F.data == "admin_edu")
async def edu_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        "🎓 <b>Управление обучением</b>",
        reply_markup=get_edu_admin_kb(),
    )


@router.callback_query(F.data == "edu_add_student")
async def add_student_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "📝 Введите ФИО нового ученика:",
        reply_markup=_back_to_edu_kb(),
    )
    await state.set_state(AddStudentForm.waiting_for_name)


@router.message(AddStudentForm.waiting_for_name, F.text)
async def add_student_name(message: Message, state: FSMContext) -> None:
    await state.update_data(student_name=message.text.strip())
    await message.answer(
        f"ФИО <b>{message.text}</b> принято.\nВыберите программу обучения:",
        reply_markup=_package_kb(),
    )
    await state.set_state(AddStudentForm.waiting_for_package)


@router.callback_query(AddStudentForm.waiting_for_package, F.data.startswith("edu_pkg_"))
async def add_student_package(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
) -> None:
    await callback.answer()
    sessions_count = int(callback.data.split("_")[2])
    user_data = await state.get_data()
    student_name = user_data.get("student_name")

    try:
        client_id = await create_client_with_package(
            full_name=student_name,
            package_type=PackageType.EDUCATION,
            total_sessions=sessions_count,
        )
        invite_link = await create_start_link(bot, str(client_id), encode=True)
        await callback.message.edit_text(
            f"✅ Ученик <b>{student_name}</b> успешно добавлен!\n"
            f"Оплачено занятий: {sessions_count}\n\n"
            f"🔗 <b>Перешлите эту ссылку ученику для входа:</b>\n"
            f"<code>{invite_link}</code>",
            reply_markup=_back_to_edu_kb(),
        )
    except Exception:
        logger.exception("Ошибка при добавлении ученика '%s'", student_name)
        await callback.message.answer(
            "❌ Ошибка при добавлении ученика. Смотри логи.",
            reply_markup=_back_to_edu_kb(),
        )
    finally:
        await state.clear()


@router.callback_query(F.data == "edu_manage_users")
async def show_edu_users(callback: CallbackQuery) -> None:
    await callback.answer()
    users = await get_active_users_by_type(PackageType.EDUCATION)

    if not users:
        await callback.message.edit_text(
            "😔 Нет активных учеников",
            reply_markup=_back_to_edu_kb(),
        )
        return

    await callback.message.edit_text(
        "👥 <b>Выберите ученика:</b>",
        reply_markup=get_users_list_kb(users, "edu"),
    )


@router.callback_query(F.data.startswith("edu_user_"))
async def show_user_card(callback: CallbackQuery) -> None:
    await callback.answer()
    user_id = int(callback.data.split("_")[2])
    
    users = await get_active_users_by_type(PackageType.EDUCATION)
    user = next((u for u in users if u.id == user_id), None)

    if not user:
        await callback.message.edit_text("❌ Ученик не найден или перемещен в архив.", reply_markup=_back_to_edu_kb())
        return

    pkg = next((p for p in user.packages if p.status == PackageStatus.ACTIVE), None)
    
    if not pkg:
        await callback.message.edit_text("У ученика нет активного курса.", reply_markup=get_user_manage_kb(user_id, "edu"))
        return

    rem = pkg.total_sessions - pkg.used_sessions
    tot = pkg.total_sessions
    buy_date = pkg.created_at.strftime("%d.%m.%Y %H:%M") if hasattr(pkg, 'created_at') and pkg.created_at else "Нет данных"

    package_visits = [v for v in user.visits if v.package_id == pkg.id] if user.visits else []
    
    history_text = ""
    if not package_visits:
        history_text = "<i>Списаний пока не было.</i>"
    else:
        for i, v in enumerate(package_visits, 1):
            v_date = v.visit_time.strftime("%d.%m.%Y %H:%M") if v.visit_time else "Нет даты"
            history_text += f"{i}. <b>{v_date}</b> (Остаток: {v.balance_after})\n"

    text = (
        f"🎓 <b>Карточка ученика:</b> {user.full_name}\n"
        f"Услуга: Обучение\n"
        f"Дата оплаты курса: <b>{buy_date}</b>\n"
        f"Остаток занятий: <b>{rem} из {tot}</b>\n\n"
        f"📈 <b>История посещений:</b>\n"
        f"{history_text}"
    )

    await callback.message.edit_text(text, reply_markup=get_user_manage_kb(user_id, "edu"))


@router.callback_query(F.data.startswith("edu_delete_"))
async def confirm_delete_user(callback: CallbackQuery) -> None:
    user_id = int(callback.data.split("_")[2])
    await callback.message.edit_text(
        "⚠️ <b>Вы уверены?</b>\nУченик будет перемещен в архив.",
        reply_markup=get_confirm_delete_kb(user_id, "edu")
    )


@router.callback_query(F.data.startswith("edu_confirm_del_"))
async def execute_delete_user(callback: CallbackQuery) -> None:
    user_id = int(callback.data.split("_")[3])
    success = await archive_user(user_id)
    if success:
        await callback.answer("✅ Ученик перемещен в архив", show_alert=True)
    else:
        await callback.answer("❌ Ошибка удаления", show_alert=True)
    await show_edu_users(callback)


@router.callback_query(F.data.startswith("edu_deduct_"))
async def ask_deduction_time(callback: CallbackQuery) -> None:
    user_id = int(callback.data.split("_")[2])
    await callback.message.edit_text(
        "🕒 <b>Укажите время занятия:</b>\n\n"
        "Вы можете списать занятие прямо сейчас, либо указать дату и время вручную.",
        reply_markup=get_deduction_time_kb(user_id, "edu")
    )


@router.callback_query(F.data.startswith("edu_time_now_"))
async def process_deduct_now(callback: CallbackQuery) -> None:
    user_id = int(callback.data.split("_")[3])
    await _execute_deduction(callback, user_id, None) 


@router.callback_query(F.data.startswith("edu_time_custom_"))
async def process_deduct_custom_start(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = int(callback.data.split("_")[3])
    await state.update_data(deduct_user_id=user_id)
    
    await callback.message.edit_text(
        "✏️ Отправьте дату и время занятия в формате:\n"
        "<b>ДД.ММ.ГГГГ ЧЧ:ММ</b>\n\n"
        "<i>Пример: 15.08.2023 14:30</i>"
    )
    await state.set_state(EduCustomTimeForm.waiting_for_time)


@router.message(EduCustomTimeForm.waiting_for_time, F.text)
async def process_deduct_custom_finish(message: Message, state: FSMContext) -> None:
    user_data = await state.get_data()
    user_id = user_data.get("deduct_user_id")
    
    try:
        visit_time = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")
    except ValueError:
        await message.answer("❌ Неверный формат! Попробуйте снова.\nПример: 15.08.2023 14:30")
        return

    await state.clear()
    
    try:
        res = await deduct_sessions(user_id, PackageType.EDUCATION, 1, visit_time)
        if res["status"] == "success":
            status_text = "🏁 Курс завершён!" if res["completed"] else f"✅ Списано задним числом! Остаток: {res['remaining']}"
            await message.answer(status_text, reply_markup=_back_to_edu_kb())
        else:
            await message.answer(f"❌ {res['message']}", reply_markup=_back_to_edu_kb())
    except Exception:
        logger.exception("Ошибка кастомного списания user_id=%s", user_id)
        await message.answer("❌ Ошибка при списании.", reply_markup=_back_to_edu_kb())


async def _execute_deduction(callback: CallbackQuery, user_id: int, visit_time: datetime | None) -> None:
    try:
        res = await deduct_sessions(user_id, PackageType.EDUCATION, 1, visit_time)
        if res["status"] == "success":
            status = "🏁 Курс завершён!" if res["completed"] else f"✅ Списано! Остаток: {res['remaining']}"
            await callback.answer(status, show_alert=True)
            await show_edu_users(callback)
        else:
            await callback.message.edit_text(
                f"❌ {res['message']}",
                reply_markup=_back_to_edu_kb(),
            )
    except Exception:
        logger.exception("Ошибка списания user_id=%s", user_id)
        await callback.message.answer(
            "❌ Ошибка при списании. Смотри логи.",
            reply_markup=_back_to_edu_kb(),
        )
