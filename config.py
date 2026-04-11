import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла (для локальной разработки)
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
# Ссылка на базу данных, Railway выдаст её в формате postgresql://...
# Нам нужно заменить её на postgresql+asyncpg:// для асинхронной работы
DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://")

# ID супер-админов (владельцев) - сюда впишешь ваши Telegram ID
SUPERADMINS = [123456789, 987654321]
