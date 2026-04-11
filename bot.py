import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN

# Импортируем наши роутеры из папки handlers
from handlers import admin_main, admin_massage, admin_edu, user

# Импортируем функцию запуска базы данных
from database.engine import init_db

# Настраиваем базовое логирование, чтобы видеть процессы и ошибки в консоли
logging.basicConfig(level=logging.INFO)

async def main():
    # Проверяем, есть ли токен
    if not BOT_TOKEN:
        logging.error("Не найден BOT_TOKEN! Проверьте файл .env или настройки Railway.")
        return

    # Инициализируем бота. Указываем, что по умолчанию используем HTML-разметку
    bot = Bot(
        token=BOT_TOKEN, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Инициализируем диспетчер (он управляет входящими сообщениями)
    dp = Dispatcher()

    # РЕГИСТРАЦИЯ РОУТЕРОВ
    # Бот будет проверять сообщения по этим файлам сверху вниз.
    dp.include_router(admin_main.router)     # Главное меню админа
    dp.include_router(admin_massage.router)  # Логика массажа
    dp.include_router(admin_edu.router)      # Логика обучения
    dp.include_router(user.router)           # Клиентская часть

    # Подключаем базу данных и создаем таблицы (если их еще нет)
    logging.info("Подключение к базе данных PostgreSQL...")
    await init_db()
    logging.info("База данных готова!")

    # Запускаем бота
    logging.info("Бот успешно запущен и готов к работе! 🚀")
    
    # Эта команда очищает старые сообщения, которые пришли, пока бот был выключен
    await bot.delete_webhook(drop_pending_updates=True) 
    
    # Начинаем слушать сервера Telegram
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        # Запускаем асинхронную функцию main()
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен вручную.")
