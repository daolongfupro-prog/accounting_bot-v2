from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from aiogram.utils.deep_linking import decode_payload

from config import settings
from database.models import User, PackageType, PackageStatus # Добавили импорт Enums
from database.requests import link_telegram_id, update_user_language
from middlewares.i18n import TEXTS

logger = logging.getLogger(__name__)
router = Router()

# --- Клавиатуры ---

def get_user_main_kb(lang: str = "ru") -> ReplyKeyboardMarkup:
    t = TEXTS.get(lang, TEXTS["ru"])
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t["balance"])],
            [KeyboardButton(text=t["change_lang"])],
        ],
        resize_keyboard=True,
    )

def get_language_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz")],
            [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
        ]
    )


# --- Хендлеры ---

@router.message(CommandStart())
async def cmd_start_unified(
    message: Message,
    command: CommandObject,
    db_user: User | None,
    texts: dict,
) -> None:
    # 1. ПРОВЕРЯЕМ ДИПЛИНК (Пришел ли человек по ссылке)
    if command.args:
        try:
            db_user_id = int(decode_payload(command.args))
            user = await link_telegram_id(db_user_id, message.from_user.id)
            if user:
                # Если язык еще не выбран, используем русский по умолчанию для приветствия
                lang = user.language if user.language else "ru"
                t = TEXTS.get(lang, TEXTS["ru"])
                await message.answer(
                    t["greeting"].format(name=user.full_name),
                    reply_markup=get_language_kb(),
                    parse_mode="HTML"
                )
            else:
                await message.answer(texts["invalid_link"])
            return
        except Exception:
            logger.exception("Ошибка deep link tg_id=%s", message.from_user.id)
            await message.answer(texts["invalid_link"])
            return

    # 2. ОБЫЧНЫЙ СТАРТ (Без ссылки)
    if message.from_user.id in settings.SUPERADMIN_IDS:
        await message.answer("⚙️ Режим администратора: /admin", reply_markup=get_user_main_kb("ru"))
        return

    if db_user:
        lang = db_user.language if db_user.language in TEXTS else "ru"
        t = TEXTS.get(lang, TEXTS["ru"])
        await message.answer(
            t["welcome_back"].format(name=db_user.full_name),
            reply_markup=get_user_main_kb(lang),
        )
    else:
        await message.answer(texts["access_denied"])


@router.callback_query(F.data.startswith("lang_"))
async def process_language_selection(
    callback: CallbackQuery,
    texts: dict,
) -> None:
    lang_code = callback.data.split("_")[1]
    await update_user_language(callback.from_user.id, lang_code)
    new_texts = TEXTS.get(lang_code, TEXTS["ru"])
    await callback.message.answer(
        new_texts["lang_set"],
        reply_markup=get_user_main_kb(lang_code),
    )
    await callback.message.delete()
    await callback.answer()


@router.message(F.text.in_({t["balance"] for t in TEXTS.values()}))
async def show_profile(
    message: Message,
    db_user: User | None,
    texts: dict,
) -> None:
    if not db_user or not db_user.packages:
        await message.answer(texts["no_services"])
        return

    lang = db_user.language if db_user.language in TEXTS else "ru"
    t = TEXTS[lang]
    lines = [t["profile_head"], ""]

    for p in db_user.packages:
        # ИСПОЛЬЗУЕМ СТРОГИЕ ENUMS
        name = t["massage"] if p.package_type == PackageType.MASSAGE else t["edu"]
        rem = p.total_sessions - p.used_sessions
        status = t["active"] if p.status == PackageStatus.ACTIVE else t["completed"]
        lines.append(f"{name}\n{t['rem']}: <b>{rem}</b> {t['of']} {p.total_sessions}\n{status}\n")

    # ИСПРАВЛЕН БАГ: Добавили parse_mode="HTML"
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(F.text.in_({t["change_lang"] for t in TEXTS.values()}))
async def change_lang(
    message: Message,
    texts: dict,
) -> None:
    await message.answer(texts["choose_lang"], reply_markup=get_language_kb())
