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
    user_data = await state.get_data()
    client_name = user_data.get("client_name")

    try:
        client_id = await create_client_with_package(
            full_name=client_name,
            package_type=PackageType.MASSAGE,
            total_sessions=sessions_count,
        )
        invite_link = await create_start_link(bot, str(client_id), encode=True)
        await callback.message.edit_text(
            f"✅ Клиент <b>{client_name}</b> успешно добавлен!\n"
            f"Оплачено сеансов: {sessions_count}\n\n"
            f"🔗 <b>Перешлите эту ссылку клиенту для входа:</b>\n"
            f"<code>{invite_link}</code>",
            reply_markup=_back_to_massage_kb(),
        )
        logger.info("Добавлен клиент массажа '%s' id=%s сеансов=%s", client_name, client_id, sessions_count)
    except Exception:
        logger.exception("Ошибка при добавлении клиента '%s'", client_name)
        await callback.message.answer(
            "❌ Ошибка при добавлении клиента. Смотри логи.",
            reply_markup=_back_to_massage_kb(),
        )
    finally:
        await state.clear()


# ==========================================
# 3. УПРАВЛЕНИЕ КЛИЕНТАМИ (СПИСОК И КАРТОЧКА)
# ==========================================
@router.callback_query(F.data == "massage_manage_users")
async def show_massage_users(callback: CallbackQuery) -> None:
    await callback.answer()
    users = await get_active_users_by_type(PackageType.MASSAGE)

    if not users:
        await callback.message.edit_text(
            "😔 Нет активных клиентов массажа",
            reply_markup=_back_to_massage_kb(),
        )
        return

    await callback.message.edit_text(
        "👥 <b>Выберите клиента:</b>",
        reply_markup=get_users_list_kb(users, "msg"),
    )


@router.callback_query(F.data.startswith("msg_user_"))
async def show_user_card(callback: CallbackQuery) -> None:
    await callback.answer()
    user_id = int(callback.data.split("_")[2])
    
    users = await get_active_users_by_type(PackageType.MASSAGE)
    user = next((u for u in users if u.id == user_id), None)

    if not user:
        await callback.message.edit_text("❌ Клиент не найден или перемещен в архив.", reply_markup=_back_to_massage_kb())
        return

    pkg = next((p for p in user.packages if p.status == PackageStatus.ACTIVE), None)
    rem = pkg.remaining_sessions if pkg else 0
    tot = pkg.total_sessions if pkg else 0

    text = (
        f"👤 <b>Карточка клиента:</b> {user.full_name}\n"
        f"Услуга: Массаж\n"
        f"Остаток сеансов: <b>{rem} из {tot}</b>"
    )

    await callback.message.edit_text(text, reply_markup=get_user_manage_kb(user_id, "msg"))


# ==========================================
# 4. УДАЛЕНИЕ КЛИЕНТА (АРХИВАЦИЯ)
# ==========================================
@router.callback_query(F.data.startswith("msg_delete_"))
async def confirm_delete_user(callback: CallbackQuery) -> None:
    user_id = int(callback.data.split("_")[2])
    await callback.message.edit_text(
        "⚠️ <b>Вы уверены?</b>\nКлиент будет перемещен в архив. Он исчезнет из списков, но останется в Excel выгрузке.",
        reply_markup=get_confirm_delete_kb(user_id, "msg")
    )


@router.callback_query(F.data.startswith("msg_confirm_del_"))
async def execute_delete_user(callback: CallbackQuery) -> None:
    user_id = int(callback.data.split("_")[3])
    success = await archive_user(user_id)
    
    if success:
        await callback.answer("✅ Клиент перемещен в архив", show_alert=True)
    else:
        await callback.answer("❌ Ошибка удаления", show_alert=True)
        
    await show_massage_users(callback) # Возвращаем к списку


# ==========================================
# 5. СПИСАНИЕ СЕАНСА (ВЫБОР ВРЕМЕНИ)
# ==========================================
@router.callback_query(F.data.startswith("msg_deduct_"))
async def ask_deduction_time(callback: CallbackQuery) -> None:
    user_id = int(callback.data.split("_")[2])
    await callback.message.edit_text(
        "🕒 <b>Укажите время визита:</b>\n\n"
        "Вы можете списать сеанс прямо сейчас, либо указать дату и время вручную (например, если забыли списать вчера).",
        reply_markup=get_deduction_time_kb(user_id, "msg")
    )


@router.callback_query(F.data.startswith("msg_time_now_"))
async def process_deduct_now(callback: CallbackQuery) -> None:
    user_id = int(callback.data.split("_")[3])
    # Передаем None, БД сама подставит func.now()
    await _execute_deduction(callback, user_id, None) 


@router.callback_query(F.data.startswith("msg_time_custom_"))
async def process_deduct_custom_start(callback: CallbackQuery, state: FSMContext) -> None:
    user_id = int(callback.data.split("_")[3])
    await state.update_data(deduct_user_id=user_id)
    
    await callback.message.edit_text(
        "✏️ Отправьте дату и время визита в формате:\n"
        "<b>ДД.ММ.ГГГГ ЧЧ:ММ</b>\n\n"
        "<i>Пример: 15.08.2023 14:30</i>"
    )
    await state.set_state(CustomTimeForm.waiting_for_time)


@router.message(CustomTimeForm.waiting_for_time, F.text)
async def process_deduct_custom_finish(message: Message, state: FSMContext) -> None:
    user_data = await state.get_data()
    user_id = user_data.get("deduct_user_id")
    
    try:
        # Пытаемся распарсить дату, которую ввел админ
        visit_time = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")
    except ValueError:
        await message.answer("❌ Неверный формат! Попробуйте снова.\nПример: 15.08.2023 14:30")
        return

    await state.clear()
    
    # Чтобы использовать нашу общую функцию логики ответа
    # Создадим "фейковый" callback_query объект для вызова
    # Либо просто вызовем нужный функционал напрямую:
    try:
        res = await deduct_sessions(user_id, PackageType.MASSAGE, 1, visit_time)
        if res["status"] == "success":
            status_text = "🏁 Пакет завершён!" if res["completed"] else f"✅ Списано задним числом! Остаток: {res['remaining']}"
            await message.answer(status_text, reply_markup=_back_to_massage_kb())
        else:
            await message.answer(f"❌ {res['message']}", reply_markup=_back_to_massage_kb())
    except Exception:
        logger.exception("Ошибка кастомного списания user_id=%s", user_id)
        await message.answer("❌ Ошибка при списании.", reply_markup=_back_to_massage_kb())


# --- Внутренняя функция для обработки результата списания ---
async def _execute_deduction(callback: CallbackQuery, user_id: int, visit_time: datetime | None) -> None:
    try:
        res = await deduct_sessions(user_id, PackageType.MASSAGE, 1, visit_time)
        if res["status"] == "success":
            status = "🏁 Пакет завершён!" if res["completed"] else f"✅ Списано! Остаток: {res['remaining']}"
            await callback.answer(status, show_alert=True)
            await show_massage_users(callback) # Возвращаем к списку
        else:
            await callback.message.edit_text(
                f"❌ {res['message']}",
                reply_markup=_back_to_massage_kb(),
            )
    except Exception:
        logger.exception("Ошибка списания user_id=%s", user_id)
        await callback.message.answer(
            "❌ Ошибка при списании. Смотри логи.",
            reply_markup=_back_to_massage_kb(),
        )
