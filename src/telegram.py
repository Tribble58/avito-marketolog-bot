import logging

from aiogram import Bot, Dispatcher

from routers import router
from config import Settings


async def run_bot():
    # Включаем логирование, чтобы не пропустить важные сообщения
    logging.basicConfig(level=logging.INFO)
    # Объект бота
    bot = Bot(token=Settings.bot_token)
    # Диспетчер
    dp = Dispatcher()
    # Прокидывание роутера в диспетчер
    dp.include_router(router)
    # Запуск процесса поллинга новых апдейтов
    await dp.start_polling(bot)
