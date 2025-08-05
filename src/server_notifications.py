import logging

logger = logging.getLogger(__name__)

from aiogram import Bot
from fastapi import FastAPI, Request, HTTPException
from src.database import Database

API_ENDPOINT = "/avito/notifications"
tg_id = None


def setup_server(tg_bot_notifications: Bot):
    """
    Runs FastAPI server, listens to any messages and sends them to notifications bot
    :param tg_bot_notifications:
    :return:
    """
    app = FastAPI()
    db = Database()
    @app.post(API_ENDPOINT)
    async def avito_webhook(request: Request):
        global tg_id
        try:
            data = await request.json()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

        # Log data
        logger.info(f"Получено уведомление от Авито: {data}")

        avito_id = data["payload"]["value"]["user_id"]
        message = data["payload"]["value"]["content"]["text"]

        logger.debug(f"Сообщение для пользователя {avito_id}: {message}")
        logger.debug(f"tg_id: {tg_id}")

        if tg_id is None:
            tg_id = await db.get_tg_id_by_account(avito_id=avito_id)
            logger.debug(f"Идентификатор пользователя в Телеграм получен!")

        if tg_id is not None:
            try:
                await tg_bot_notifications.send_message(chat_id=tg_id, text=f"📨 Новое сообщение от клиента Авито!\n\n{message}")
            except Exception as e:
                print(f"Ошибка при отправке сообщения: {e}")
        else:
            logger.warning(f"Аккаунт {avito_id} не подключен ни к одному пользователю!")

    return app
