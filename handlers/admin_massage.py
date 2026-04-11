from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.deep_linking import create_start_link

router = Router()

# --- FSM (Машина состояний) для добавления клиента ---
class AddClientForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_package = State()

# --- ДОБАВЛЕНИЕ КЛИЕНТА ---

@router.callback_query(F.data == "msg_add_client")
async def start_adding_client(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📝 <b>Добавление нового VIP-клиента</b>\n\n"
        "Введите Имя и Фамилию клиента:",
        parse_mode="HTML"
    )
    await state.set_state(AddClientForm.waiting_for_name)
    await callback.answer()

@router.message(AddClientForm.waiting_for_name)
async def process_client_name(message: Message, state: FSMContext):
    await state.update_data(client_name=message.text)
    
    packages_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="5 сеансов", callback_data="pkg_5")],
        [InlineKeyboardButton(text="10 сеансов", callback_data="pkg_10")],
        [InlineKeyboardButton(text="15 сеансов (VIP)", callback_data="pkg_15")]
    ])
    
    await message.answer(
        f"Имя <b>{message.text}</b> сохранено.\n"
        f"Выберите пакет сеансов массажа:",
        reply_markup=packages_kb,
        parse_mode="HTML"
    )
    await state.set_state(AddClientForm.waiting_for_package)

@router.callback_query(AddClientForm.waiting_for_package, F.data.startswith("pkg_"))
async def process_client_package(callback: CallbackQuery, state: FSMContext, bot: Bot):
    sessions_count = int(callback.data.split("_")[1])
    data = await state.get_data()
    client_name = data['client_name']
    
    # TODO: Запись в БД (PostgreSQL). Получение db_user_id
    db_user_id = 105 # Заглушка
    
    # Генерация зашифрованной ссылки
    link = await create_start_link(bot, str(db_user_id), encode=True)
    
    await callback.message.edit_text(
        f"✅ <b>Карточка клиента успешно создана!</b>\n\n"
        f"👤 Клиент: <b>{client_name}</b>\n"
        f"🎟 Пакет: <b>{sessions_count} сеансов</b>\n\n"
        f"🔗 <b>Ссылка для клиента:</b>\n{link}\n\n"
        f"<i>Отправьте эту ссылку клиенту. Когда он перейдет по ней, бот автоматически его узнает.</i>",
        parse_mode="HTML"
    )
    await state.clear()
    await callback.answer()

# --- СПИСАНИЕ СЕАНСОВ ---

@router.callback_query(F.data == "msg_deduct")
async def show_clients_for_deduction(callback: CallbackQuery):
    # TODO: Получение списка активных клиентов из БД
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Иван Иванов (остаток: 5)", callback_data="deduct_user_105")],
        [InlineKeyboardButton(text="👤 Анна Смирнова (остаток: 2)", callback_data="deduct_user_106")],
        [InlineKeyboardButton(text="🔙 Назад в меню массажа", callback_data="admin_massage")]
    ])
    
    await callback.message.edit_text("Выберите клиента для списания сеанса:", reply_markup=kb)

@router.callback_query(F.data.startswith("deduct_user_"))
async def confirm_deduction(callback: CallbackQuery):
    user_id = callback.data.split("_")[2]
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1 сеанс", callback_data=f"confirm_dec_{user_id}_1"),
            InlineKeyboardButton(text="2 сеанса", callback_data=f"confirm_dec_{user_id}_2")
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="msg_deduct")]
    ])
    
    await callback.message.edit_text(f"Сколько сеансов списать?", reply_markup=kb)

# TODO: Добавить обработчик для confirm_dec_... (само списание в БД)
