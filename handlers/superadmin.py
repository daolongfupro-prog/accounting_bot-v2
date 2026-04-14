from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import settings
from database.models import PackageType
from database.requests import get_active_users_by_type, get_all_data_for_export
from handlers.admin_massage import IsAdmin

logger = logging.getLogger(__name__)
router = Router()


class BroadcastForm(StatesGroup):
    waiting_for_text = State()


def get_superadmin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Общая статистика", callback_data="sa_stats")],
            [InlineKeyboardButton(text="📢 Рассылка всем", callback_data="sa_broadcast")],
            [InlineKeyboardButton(text="🔙 В админ панель", callback_data="admin_main")],
        ]
    )


@router.message(IsAdmin(), Command("superadmin"))
async def superadmin_panel(message: Message) -> None:
    if message.from_user.id not in settings.SUPERADMIN_IDS:
        return
    await message.answer(
        "🔐 <b>Панель суперадминистратора</b>",
        reply_markup=get_superadmin_kb(),
    )


@router.callback_query(IsAdmin(), F.data == "sa_stats")
async def show_stats(callback: CallbackQuery) -> None:
    all_users = await get_all_data_for_export()
    massage_users = await get_active_users_by_type(PackageType.MASSAGE)
    edu_users = await get_active_users_by_type(PackageType.EDUCATION)

    total = len(all_users)
    active_massage = len(massage_users)
    active_edu = len(edu_users)
    linked = sum(1 for u in all_users if u.telegram_id)

    await callback.message.edit_text(
        f"📊 <b>Общая статистика</b>\n\n"
        f"👥 Всего клиентов: <b>{total}</b>\n"
        f"🔗 Привязали Telegram: <b>{linked}</b>\n"
        f"💆‍♂️ Активных массажей: <b>{active_massage}</b>\n"
        f"🎓 Активных обучений: <b>{active_edu}</b>",
        reply_markup=get_superadmin_kb(),
    )
    await callback.answer()


@router.callback_query(IsAdmin(), F.data == "sa_broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "📢 Введите текст рассылки.\n"
        "Сообщение получат все пользователи с привязанным Telegram.\n\n"
        "Для отмены напишите /cancel"
    )
    await state.set_state(BroadcastForm.waiting_for_text)
    await callback.answer()


@router.message(IsAdmin(), BroadcastForm.waiting_for_text)
async def broadcast_send(message: Message, state: FSMContext) -> None:
    from aiogram import Bot
    bot: Bot = message.bot

    all_users = await get_all_data_for_export()
    targets = [u for u in all_users if u.telegram_id]

    sent, failed = 0, 0
    for user in targets:
        try:
            await bot.send_message(user.telegram_id, message.text)
            sent += 1
        except Exception:
            failed += 1
            logger.warning("Не удалось отправить сообщение tg_id=%s", user.telegram_id)

    await state.clear()
    await message.answer(
        f"📢 Рассылка завершена!\n"
        f"✅ Отправлено: <b>{sent}</b>\n"
        f"❌ Не доставлено: <b>{failed}</b>",
        reply_markup=get_superadmin_kb(),
    )
    logger.info("Рассылка завершена: sent=%s failed=%s", sent, failed)
