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


class IsAdmin(Filter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return event.from_user.id in settings.SUPERADMIN_IDS


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


@router.callback_query(F.data == "admin_massage")
async def massage_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        "💆‍♀️ <b>Управление массажем</b>",
        reply_markup=get_massage_admin_kb(),
    )


@router.callback_query(F.data == "msg_add_client")
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


@router.callback_query(F.data == "msg_deduct")
async def show_massage_clients(callback: CallbackQuery) -> None:
    await callback.answer()
    users = await get_active_users_by_type(PackageType.MASSAGE)

    if not users:
        await callback.message.edit_text(
            "😔 Нет активных клиентов массажа",
            reply_markup=_back_to_massage_kb(),
        )
        return

    kb = []
    for u in users:
        pkg = next(
            (p for p in u.packages
             if p.package_type == PackageType.MASSAGE
             and p.status == PackageStatus.ACTIVE),
            None,
        )
        if not pkg:
            continue
        kb.append([InlineKeyboardButton(
            text=f"👤 {u.full_name} (остаток: {pkg.remaining_sessions})",
            callback_data=f"msg_dec_{u.id}",
        )])

    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_massage")])
    await callback.message.edit_text(
        "👇 Выберите клиента для списания:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
    )


@router.callback_query(F.data.startswith("msg_dec_"))
async def process_msg_deduction(callback: CallbackQuery) -> None:
    await callback.answer()
    user_id = int(callback.data.split("_")[2])

    try:
        res = await deduct_sessions(user_id, PackageType.MASSAGE, 1)
        if res["status"] == "success":
            status = "🏁 Пакет завершён!" if res["completed"] else f"✅ Списано! Остаток: {res['remaining']}"
            await callback.answer(status, show_alert=True)
            await show_massage_clients(callback)
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
