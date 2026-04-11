from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.deep_linking import decode_payload

router = Router()

def get_language_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")]
    ])

# --- АВТОРИЗАЦИЯ И ВЫБОР ЯЗЫКА ---

@router.message(CommandStart(deep_link=True))
async def cmd_start_deep_link(message: Message, command: CommandObject):
    args = command.args
    try:
        db_user_id = int(decode_payload(args))
        # TODO: Привязать message.from_user.id к db_user_id в базе данных
        client_name = "Иван" # Заглушка
        
        await message.answer(
            f"👋 Добро пожаловать, <b>{client_name}</b>!\n\n"
            "Пожалуйста, выберите язык интерфейса\n"
            "Iltimos, tilni tanlang\n"
            "Please choose a language:",
            reply_markup=get_language_kb(),
            parse_mode="HTML"
        )
    except Exception:
        await message.answer("❌ Ошибка: неверная или устаревшая ссылка.")

@router.message(CommandStart())
async def cmd_start_normal(message: Message):
    # TODO: Проверка, есть ли юзер в базе. Если есть - показать главное меню.
    await message.answer(
        "🔒 Здравствуйте! Этот бот работает только по персональным приглашениям.\n"
        "Пожалуйста, обратитесь к администратору для получения доступа."
    )

@router.callback_query(F.data.startswith("lang_"))
async def process_language_selection(callback: CallbackQuery):
    lang_code = callback.data.split("_")[1] 
    # TODO: Сохранить язык в БД
    
    if lang_code == "ru":
        text = "✅ Язык успешно установлен!\n\nНажмите /profile, чтобы посмотреть остаток сеансов."
    elif lang_code == "uz":
        text = "✅ Til muvaffaqiyatli o'rnatildi!\n\nSeanslar qoldig'ini ko'rish uchun /profile tugmasini bosing."
    else:
        text = "✅ Language successfully set!\n\nClick /profile to see your remaining sessions."
        
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()

# --- ЛИЧНЫЙ КАБИНЕТ КЛИЕНТА ---

@router.message(F.text.in_(["📊 Мой остаток", "/profile"]))
async def show_user_profile(message: Message):
    # TODO: Достать данные клиента из БД
    user_name = "Иван"
    remaining = 4
    total = 10
    last_visit = "10.04.2024"
    
    profile_text = (
        f"<b>👤 Личный кабинет: {user_name}</b>\n\n"
        f"🎟 Пакет: <b>{total} сеансов</b>\n"
        f"✅ Осталось: <b>{remaining} сеансов</b>\n"
        f"📅 Последний визит: <code>{last_visit}</code>\n\n"
        f"<i>При остатке 2 сеанса я пришлю вам уведомление!</i>"
    )
    
    await message.answer(profile_text, parse_mode="HTML")
