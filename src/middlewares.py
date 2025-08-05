import logging

from avito import AvitoAccount

logger = logging.getLogger(__name__)

from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from src.database import Database


class DbOuterMiddleware(BaseMiddleware):
    """
    Middleware for putting User to database
    """
    def __init__(self, db):
        self.db: Database = db

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        logger.debug(f"Вызываю {DbOuterMiddleware.__name__}")
        tg_id = event.from_user.id
        user = await self.db.get_user_id(tg_id=tg_id)
        if not user:
            # TODO: add user and avito_user_id at one time
            # Add row to User table
            logger.info("User is new. Creating user...")
            await self.db.insert_user(tg_id=tg_id)
        else:
            logger.info("User exists!")

        data["db"] = self.db
        data["tg_id"] = tg_id
        result = await handler(event, data)
        return result


class AvitoInnerMiddleware(BaseMiddleware):
    """
    Middleware for initializing AvitoClient class
    """
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        logger.debug(f"Вызываю {AvitoInnerMiddleware.__name__}")
        # Get database instance from DbOuterMiddleware
        db = data["db"]
        tg_id = data["tg_id"]

        # Check that previous router had callback data
        if "callback_data" not in data:
            logger.debug("callback_data не найдено, пропускаю AvitoInnerMiddleware")
            return await handler(event, data)

        avito_id = data["callback_data"].avito_id

        # client_id = data["callback_data"].client_id
        # client_secret = data["callback_data"].client_secret

        client_id, client_secret = await db.get_account_secrets(tg_id=tg_id, avito_id=avito_id)

        avito_account = AvitoAccount()
        await avito_account.set_client_id(client_id=client_id)
        await avito_account.set_client_secret(client_secret=client_secret)
        await avito_account.run_session()
        data["avito_account"] = avito_account
        result = await handler(event, data)
        await avito_account.close_session()
        return result
