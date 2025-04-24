import logging

from aiogram.types import BotCommand

from src.bot import router, commands_router, router
from src.middlewares import TgUserCheckMiddleware, DbMiddleware

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s - [%(levelname)s] -  %(name)s"
                           "- (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s")
logger = logging.getLogger(__name__)

import asyncio
from aiogram import Bot, Dispatcher

from src.config import Settings

from src.database import PostgresDatabase

user_sessions: dict = {}

db = PostgresDatabase()


async def on_startup():
    """
    Запускает поллинг, задает меню.
    """

    async def set_menu_commands(bot: Bot):
        """
        Задает меню бота для навигации.
        """
        logger.debug("Создание меню...")
        await bot.set_my_commands(
            commands=
            [
                BotCommand(command="get_unread_messages", description="🍌Получить непрочитанные чаты"),
                BotCommand(command="templates_editor", description="🥭Редактор шаблонов"),
                BotCommand(command="accounts_manager", description="🍉Управление аккаунтами"),
                BotCommand(command="support", description="🍏Поддержка"),
                BotCommand(command="something", description="⚙️Че-то"),
            ]
        )
        logger.debug("Меню создано!")

    tg_bot = Bot(token=Settings.bot_token)

    dp = Dispatcher()
    # dp.include_router(router)
    dp.include_router(commands_router)
    dp.include_router(router)

    await db.init_models()
    await set_menu_commands(tg_bot)

    dp["user_sessions"] = user_sessions
    dp["db"] = db
    commands_router.message.middleware(TgUserCheckMiddleware(db))
    router.callback_query.middleware(DbMiddleware(db))
    router.message.middleware(DbMiddleware(db))

    # Пропуск апдейтов, которые были отправлены во время отключения бота
    await tg_bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(tg_bot)


if __name__ == "__main__":
    asyncio.run(on_startup())
