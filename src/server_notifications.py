import logging

logger = logging.getLogger(__name__)

from aiogram import Bot
from fastapi import FastAPI, Request, HTTPException
from database import Database

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

        user_id = data["payload"]["value"]["user_id"]
        author_id = data["payload"]["value"]["author_id"]

        message = data["payload"]["value"]["content"]["text"]

        # Skip messages that were sent by owner of the account
        if user_id != author_id:
            logger.debug(f"Сообщение для пользователя {user_id}: {message}")
            logger.debug(f"tg_id: {tg_id}")

            # Get id of user whom notification needs to be sent to. If there are multiple users that manage one
            # account, iterate and send notification to each of them

            if tg_id is None:
                tg_id = await db.get_tg_id_by_account(avito_id=user_id)
                logger.debug(f"Идентификатор пользователя в Телеграм получен!")

            if tg_id is not None:
                try:
                    for (chat_id,) in tg_id:
                        await tg_bot_notifications.send_message(chat_id=chat_id,
                                                                text=f"📨 Новое сообщение от клиента Авито!\n\n{message}")
                        logger.info(f"Сообщение пользователя аккаунта : {chat_id}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке сообщения: {e}")
            else:
                logger.warning(f"Аккаунт {user_id} не подключен ни к одному пользователю!")
        else:
            logger.info(f"Сообщение пользователя аккаунта : {data}")

    return app
