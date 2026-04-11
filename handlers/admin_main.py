import io
import openpyxl
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from keyboards.admin_kb import get_main_admin_kb
from config import SUPERADMINS
from database.requests import get_all_data_for_export

router = Router()

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id not in SUPERADMINS: return 
    await message.answer("🌟 <b>Панель управления администратора</b>", 
                         reply_markup=get_main_admin_kb(), 
                         parse_mode="HTML")

@router.callback_query(F.data == "admin_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text("🌟 <b>Панель управления администратора</b>", 
                                     reply_markup=get_main_admin_kb(), 
                                     parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin_backup")
async def export_excel(callback: CallbackQuery):
    users = await get_all_data_for_export()
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Studio Backup"
    ws.append(["ID Юзера", "Имя Клиента", "Тип Услуги", "Всего", "Использовано", "Остаток", "Статус"])

    for u in users:
        if not u.packages:
            ws.append([u.id, u.full_name, "Нет услуг", 0, 0, 0, "N/A"])
        for p in u.packages:
            ws.append([
                u.id, 
                u.full_name, 
                "Массаж" if p.package_type == "massage" else "Обучение", 
                p.total_sessions, 
                p.used_sessions, 
                p.total_sessions - p.used_sessions, 
                p.status
            ])

    file_stream = io.BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)
    
    await callback.message.answer_document(
        BufferedInputFile(file_stream.read(), filename="studio_backup.xlsx"),
        caption="📁 <b>Актуальный бэкап базы данных</b>",
        parse_mode="HTML"
    )
    await callback.answer()
