import logging

from src.avito import AvitoUser

logger = logging.getLogger(__name__)

from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from src.database import PostgresDatabase


class TgUserCheckMiddleware(BaseMiddleware):
    """
    Puts TG user to database, adds AVITO id to it
    """
    def __init__(self, db):
        self.db: PostgresDatabase = db

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        logger.debug(f"Вызываю {TgUserCheckMiddleware.__name__}")
        tg_id = event.from_user.id
        user = await self.db.get_user_id(tg_id=tg_id)
        if not user:

            # TODO: add user and avito_user_id at one time

            # Add row to TgUser table
            await self.db.set_user(tg_id=tg_id)

        avito_user = AvitoUser()
        await avito_user.run_session()
        avito_id = avito_user.avito_id
        # Put avvito_id to the corresponding user
        if not await self.db.get_avito_id(tg_id=tg_id):
            await self.db.set_avito_id(tg_id=tg_id, avito_id=avito_id)

        data["db"] = self.db
        data["tg_id"] = tg_id
        data["avito_id"] = avito_id
        data["avito_user"] = avito_user
        result = await handler(event, data)
        await avito_user.close_session()

        # ...
        # Здесь выполняется код на выходе из middleware
        # ...
        return result

class DbMiddleware(BaseMiddleware):
    """
    Middleware for providing handlers with db and AvitoUser class
    """
    def __init__(self, db):
        self.db: PostgresDatabase = db

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        logger.debug(f"Вызываю {DbMiddleware.__name__}")

        tg_id = event.from_user.id
        avito_user = AvitoUser()
        await avito_user.run_session()
        avito_id = await self.db.get_avito_id(tg_id=tg_id)
        avito_user.avito_id = avito_id
        data["db"] = self.db
        data["avito_user"] = avito_user

        result = await handler(event, data)
        await avito_user.close_session()
        return result