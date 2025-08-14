import logging
import subprocess
import time

import aiohttp
import uvicorn
from aiogram.types import BotCommand

from bot import router
from middlewares import AvitoInnerMiddleware
from middlewares import DbOuterMiddleware
from routers.accounts_manager import accounts_manager_router
from routers.chat_manager import chat_manager_router, avito_service_router
from routers.notifications import notifications_router
from routers.templates_editor import templates_editor_router
from server_notifications import setup_server, API_ENDPOINT

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s - [%(levelname)s] -  %(name)s"
                           "- (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s")
logger = logging.getLogger(__name__)

import asyncio
from aiogram import Bot, Dispatcher
from config import Settings
from database import Database

db = Database()


async def on_startup():
    """
    Starts polling, sets up menus, starts server and ngrok
    """

    async def set_menu_commands(bot: Bot):
        """
        Sets up a menu for main bot
        :param bot:
        :return:
        """
        logger.debug("Создание меню...")
        await bot.set_my_commands(
            commands=
            [
                BotCommand(command="chat_manager", description="▫️Непрочитанные сообщения"),
                BotCommand(command="templates_editor", description="▫️Редактор шаблонов"),
                BotCommand(command="accounts_manager", description="▫️Управление аккаунтами"),
                BotCommand(command="support", description="▫️Поддержка"),
                # BotCommand(command="something", description="⚙️Че-то"),
            ]
        )
        logger.debug("Меню создано!")

    async def set_menu_commands_for_notifications(bot: Bot):
        """
        Sets up a menu for notifications bot
        :param bot:
        :return:
        """
        logger.debug("Создание меню для уведомлений...")
        await bot.set_my_commands(
            commands=
            [
                BotCommand(command="subscribe", description="🔔Подписаться на уведомления всех Ваших клиентов Авито"),
                BotCommand(command="unsubscribe", description="🔕Отписаться от уведомлений всех Ваших клиентов Авито"),
            ]
        )
        logger.debug("Меню для уведомлений создано!")

    async def run_fastapi(app):
        """
        Sets up a local server
        :param app:
        :return:
        """
        config = uvicorn.Config(app=app, host="0.0.0.0", port=8080, log_level="info")
        server = uvicorn.Server(config)
        logger.info(f"Сервер запущен!")
        await server.serve()

    async def get_ngrok_url():
        """
        Runs ngrok that forwards local server to public
        :return:
        """
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:4040/api/tunnels") as resp:
                data = await resp.json()
                public_url = data["tunnels"][0]["public_url"]
                logger.info(f"NGROK запущен: {public_url}")
                return public_url

    tg_bot = Bot(token=Settings.bot_token)

    dp = Dispatcher()

    dp.include_router(chat_manager_router)
    dp.include_router(accounts_manager_router)
    dp.include_router(avito_service_router)
    dp.include_router(templates_editor_router)

    await db.init_models()
    await set_menu_commands(tg_bot)

    dp["db"] = db
    # commands_router.message.outer_middleware(DbOuterMiddleware(db))
    chat_manager_router.message.outer_middleware(DbOuterMiddleware(db))
    chat_manager_router.callback_query.outer_middleware(DbOuterMiddleware(db))
    avito_service_router.callback_query.outer_middleware(DbOuterMiddleware(db))
    avito_service_router.callback_query.middleware(AvitoInnerMiddleware())
    templates_editor_router.message.outer_middleware(DbOuterMiddleware(db))
    templates_editor_router.callback_query.outer_middleware(DbOuterMiddleware(db))
    router.callback_query.outer_middleware(DbOuterMiddleware(db))
    router.message.outer_middleware(DbOuterMiddleware(db))

    # Skip updates while bot was unavailable
    # await tg_bot.delete_webhook(drop_pending_updates=True)

    tg_bot_notifications = Bot(token=Settings.notifications_bot_token)
    dp_notifications = Dispatcher()
    dp_notifications.include_router(notifications_router)
    dp_notifications["db"] = db
    await set_menu_commands_for_notifications(tg_bot_notifications)

    # Skip updates while bot was unavailable
    # await tg_bot_notifications.delete_webhook(drop_pending_updates=True)

    # Run server with message sending functionality
    app = setup_server(tg_bot_notifications=tg_bot_notifications)

    # Run ngrok for port forwarding
    ngrok = subprocess.Popen(["ngrok", "http", "8080"])
    time.sleep(3) # wait for ngrok to run up

    # Get public address and put it to notification bot
    server_url = await get_ngrok_url()
    dp_notifications["server_url"] = server_url + API_ENDPOINT

    # Run everything
    try:
        await asyncio.gather(
            dp.start_polling(tg_bot),
            dp_notifications.start_polling(tg_bot_notifications),
            run_fastapi(app)
        )
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Shutdown commenced...")
    finally:
        await db.close()
        await tg_bot.session.close()
        await tg_bot_notifications.session.close()


if __name__ == "__main__":
    asyncio.run(on_startup())
