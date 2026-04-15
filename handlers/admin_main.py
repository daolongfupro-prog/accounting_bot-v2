from __future__ import annotations

import io
import logging
from datetime import datetime

import openpyxl
from openpyxl.styles import Font
from aiogram import F, Router
from aiogram.filters import Command, Filter
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from config import settings
from database.models import PackageType
from database.requests import get_all_data_for_export
from keyboards.admin_kb import get_main_admin_kb

logger = logging.getLogger(__name__)
router = Router()


# Универсальный фильтр админа для всего роутера
class IsAdmin(Filter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return event.from_user.id in settings.SUPERADMIN_IDS

router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    await message.answer(
        "🌟 <b>Панель управления администратора</b>",
        reply_markup=get_main_admin_kb(),
    )


@router.callback_query(F.data == "admin_main")
async def back_to_main(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "🌟 <b>Панель управления администратора</b>",
        reply_markup=get_main_admin_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_backup")
async def export_excel(callback: CallbackQuery) -> None:
    await callback.answer("⏳ Генерирую детализированный отчет...")

    users = await get_all_data_for_export()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Журнал посещений"
    
    # Формируем заголовки по нашему ТЗ
    headers = [
        "Имя клиента / Ученика", 
        "Статус профиля", 
        "Тип услуги", 
        "Дата оплаты пакета", 
        "Дата и время визита", 
        "Списание", 
        "Остаток занятий"
    ]
    ws.append(headers)
    
    # Делаем заголовки жирными
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for u in users:
        archived_status = "В архиве" if u.is_archived else "Активный"
        
        if not u.packages:
            ws.append([u.full_name, archived_status, "Нет услуг", "-", "-", "-", "-"])
            continue
            
        for p in u.packages:
            p_type = "Массаж" if p.package_type == PackageType.MASSAGE else "Обучение"
            p_date = p.created_at.strftime("%d.%m.%Y %H:%M") if p.created_at else "Нет данных"
            
            if not p.visits:
                # Пакет куплен, но визитов еще не было
                ws.append([
                    u.full_name, 
                    archived_status, 
                    p_type, 
                    p_date, 
                    "Визитов пока нет", 
                    0, 
                    p.total_sessions
                ])
            else:
                # Выводим каждый визит отдельной строкой
                for v in p.visits:
                    v_date = v.visit_time.strftime("%d.%m.%Y %H:%M") if v.visit_time else "-"
                    ws.append([
                        u.full_name,
                        archived_status,
                        p_type,
                        p_date,
                        v_date,
                        v.amount,          # Всегда будет -1
                        v.balance_after    # Остаток на момент этого конкретного визита
                    ])

    # Настраиваем ширину колонок для красоты
    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 20

    # Сохраняем в память и отправляем
    file_stream = io.BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)

    filename = f"Jurnal_Posesheniy_{datetime.now().strftime('%d_%m_%Y')}.xlsx"
    await callback.message.answer_document(
        BufferedInputFile(file_stream.read(), filename=filename),
        caption="📁 <b>Детализированный журнал посещений</b>\nВсе оплаты и списания учтены.",
    )
    logger.info("Excel бэкап выгружен суперадмином tg_id=%s", callback.from_user.id)
