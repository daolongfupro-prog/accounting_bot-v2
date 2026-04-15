from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, Filter
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

logger = logging.getLogger(__name__)
router = Router()

# Универсальный фильтр для суперадмина (чтобы не зависеть от импортов из других файлов)
class IsSuperAdmin(Filter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return event.from_user.id in settings.SUPERADMIN_IDS

router.message.filter(IsSuperAdmin())
router.callback_query.filter(IsSuperAdmin())


class BroadcastForm(StatesGroup):
    waiting_for_text = State()


def get_superadmin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Общая статистика", callback_data="sa_stats")],
            [InlineKeyboardButton(text="📢 Рассылка активным", callback_data="sa_broadcast")],
            [InlineKeyboardButton(text="🔙 В админ панель", callback_data="admin_main")],
        ]
    )

def get_cancel_broadcast_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить рассылку", callback_data="sa_cancel_broadcast")]
        ]
    )


@router.message(Command("superadmin"))
async def superadmin_panel(message: Message) -> None:
    await message.answer(
        "🔐 <b>Панель суперадминистратора</b>",
        reply_markup=get_superadmin_kb(),
    )


@router.callback_query(F.data == "sa_stats")
async def show_stats(callback: CallbackQuery) -> None:
    all_users = await get_all_data_for_export()
    massage_users = await get_active_users_by_type(PackageType.MASSAGE)
    edu_users = await get_active_users_by_type(PackageType.EDUCATION)

    # Считаем активных и архивных отдельно!
    active_total = sum(1 for u in all_users if not u.is_archived)
    archived_total = sum(1 for u in all_users if u.is_archived)
    linked = sum(1 for u in all_users if u.telegram_id and not u.is_archived)
    
    active_massage = len(massage_users)
    active_edu = len(edu_users)

    await callback.message.edit_text(
        f"📊 <b>Общая статистика (Версия 2.0)</b>\n\n"
        f"👥 Всего активных клиентов: <b>{active_total}</b>\n"
        f"🗄 Клиентов в архиве: <b>{archived_total}</b>\n"
        f"🔗 Привязали Telegram (активные): <b>{linked}</b>\n"
        f"💆‍♂️ Активных массажей: <b>{active_massage}</b>\n"
        f"🎓 Активных обучений: <b>{active_edu}</b>",
        reply_markup=get_superadmin_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "sa_broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "📢 <b>Введите текст рассылки.</b>\n\n"
        "Сообщение получат ТОЛЬКО активные пользователи с привязанным Telegram (архивные исключены).",
        reply_markup=get_cancel_broadcast_kb()
    )
    await state.set_state(BroadcastForm.waiting_for_text)
    await callback.answer()


# Хэндлер для красивой отмены рассылки
@router.callback_query(BroadcastForm.waiting_for_text, F.data == "sa_cancel_broadcast")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "❌ Рассылка отменена.",
        reply_markup=get_superadmin_kb()
    )
    await callback.answer()


@router.message(BroadcastForm.waiting_for_text)
async def broadcast_send(message: Message, state: FSMContext, bot: Bot) -> None:
    # Исключаем архивных пользователей из рассылки!
    all_users = await get_all_data_for_export()
    targets = [u for u in all_users if u.telegram_id and not u.is_archived]

    if not targets:
        await message.answer("🤷‍♂️ Нет активных пользователей для рассылки.", reply_markup=get_superadmin_kb())
        await state.clear()
        return

    processing_msg = await message.answer("⏳ <i>Начинаю рассылку...</i>")

    sent, failed = 0, 0
    for user in targets:
        try:
            await bot.send_message(user.telegram_id, message.text)
            sent += 1
            # 🛡 АНТИ-БАН защита: пауза 50мс между сообщениями
            await asyncio.sleep(0.05) 
        except Exception:
            failed += 1
            logger.warning("Не удалось отправить сообщение tg_id=%s", user.telegram_id)

    await state.clear()
    await processing_msg.delete()
    await message.answer(
        f"📢 Рассылка завершена!\n"
        f"✅ Отправлено: <b>{sent}</b>\n"
        f"❌ Не доставлено: <b>{failed}</b>",
        reply_markup=get_superadmin_kb(),
    )
    logger.info("Рассылка завершена: sent=%s failed=%s", sent, failed)
