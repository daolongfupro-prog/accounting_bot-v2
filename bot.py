import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from database.engine import close_db, init_db
from handlers import admin_edu, admin_main, admin_massage, superadmin, user
from middlewares.auth import AuthMiddleware
from middlewares.i18n import I18nMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    logger.info("Инициализация базы данных...")
    await init_db()
    logger.info("Бот запущен ✅")


async def on_shutdown(bot: Bot) -> None:
    logger.info("Завершение работы...")
    await close_db()
    await bot.session.close()
    logger.info("Бот остановлен 🔌")


async def main() -> None:
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()

    # Мидлвары
    dp.message.middleware(AuthMiddleware())
    dp.message.middleware(I18nMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    dp.callback_query.middleware(I18nMiddleware())

    # Роутеры
    dp.include_router(superadmin.router)
    dp.include_router(admin_main.router)
    dp.include_router(admin_massage.router)
    dp.include_router(admin_edu.router)
    dp.include_router(user.router)

    # Хуки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную")
