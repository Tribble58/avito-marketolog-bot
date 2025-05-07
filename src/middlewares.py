import logging

logger = logging.getLogger(__name__)

from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from src.database import Database


class CommandsMiddleware(BaseMiddleware):
    """
    Middleware for putting Telegram user to database and adding Avito id to it
    """
    def __init__(self, db):
        self.db: Database = db

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        logger.debug(f"Вызываю {CommandsMiddleware.__name__}")
        tg_id = event.from_user.id
        user = await self.db.get_user_id(tg_id=tg_id)
        if not user:
            # TODO: add user and avito_user_id at one time
            # Add row to User table
            await self.db.insert_user(tg_id=tg_id)

        data["db"] = self.db
        data["tg_id"] = tg_id
        result = await handler(event, data)
        return result

class DbMiddleware(BaseMiddleware):
    """
    Middleware for providing handlers with db and AvitoUser class
    """
    def __init__(self, db):
        self.db: Database = db

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        logger.debug(f"Вызываю {DbMiddleware.__name__}")

        data["db"] = self.db
        result = await handler(event, data)
        return result