from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import get_active_users_by_type
from keyboards import get_edu_admin_kb

router = Router()

@router.callback_query(F.data == "edu_deduct_list")
async def edu_deduct_list(callback: CallbackQuery):
    students = await get_active_users_by_type("education")
    if not students:
        await callback.answer("Нет активных учеников")
        return
    
    kb = []
    for s in students:
        pkg = next(p for p in s.packages if p.package_type == "education" and p.status == "active")
        kb.append([InlineKeyboardButton(
            text=f"{s.full_name} ({pkg.total_sessions - pkg.used_sessions})", 
            callback_data=f"edu_dec_{s.id}"
        )])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_edu")])
    
    await callback.message.edit_text(
        "👇 Выберите ученика для списания:", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

@router.callback_query(F.data == "edu_stats")
async def show_edu_stats(callback: CallbackQuery):
    students = await get_active_users_by_type("education")
    text = "📊 <b>Текущие ученики:</b>\n\n"
    for s in students:
        pkg = next(p for p in s.packages if p.package_type == "education" and p.status == "active")
        text += f"👤 {s.full_name}: {pkg.used_sessions}/{pkg.total_sessions}\n"
    
    await callback.message.edit_text(
        text, 
        parse_mode="HTML", 
        reply_markup=get_edu_admin_kb()
    )
