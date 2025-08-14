import logging

logger = logging.getLogger(__name__)

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from avito import AvitoAccount
from database import Database

notifications_router = Router()

"""
This bot acts as a receiver of notifications that Avito server sends to our server by webhook.
It contains several commands represented in menu that basically implement subscription/unsubscription functions. 
"""

@notifications_router.message(Command("start"))
async def start(message: Message):
    """
    Start command with available options
    :param message:
    :return:
    """
    logger.debug("Стартовая команда")

    await message.answer("Это бот для подписки на уведомления. Вот список команд:\n\n"
                         "🔔/subscribe, чтобы подписаться на уведомления клиентов, которые Вы подключили в модуле управления аккаунтами\n"
                         "🔕/unsubscribe, чтобы отписаться от уведомлений клиентов, которые Вы подключили в модуле управления аккаунтами")


@notifications_router.message(Command("subscribe"))
async def subscribe_to_notifications(message: Message, db: Database, server_url: str):
    """
    Gets account token by secrets and subscribes for its notifications
    :param message:
    :param db:
    :param server_url:
    :return:
    """
    tg_id = message.from_user.id

    accounts = await db.get_accounts(tg_id=tg_id)
    for (avito_id,) in accounts:
        client_id, client_secret = await db.get_account_secrets(tg_id=tg_id, avito_id=avito_id)
        avito_client = AvitoAccount()
        await avito_client.set_client_id(client_id=client_id)
        await avito_client.set_client_secret(client_secret=client_secret)
        await avito_client.get_token()
        name, _ = await db.get_account_info(tg_id=tg_id, avito_id=avito_id)
        logger.info(f"Клиент {name} успешно найден!")
        await avito_client.subscribe_to_notifications(server_url=server_url)
        await avito_client.close_session()

    await message.answer("Вы подписаны на все уведомления!")


@notifications_router.message(Command("unsubscribe"))
async def unsubscribe_from_notifications(message: Message, db: Database, server_url: str):
    """
    Gets account token by secrets and unsubscribes from any notifications
    :param message:
    :param db:
    :param server_url:
    :return:
    """
    tg_id = message.from_user.id

    accounts = await db.get_accounts(tg_id=tg_id)
    for avito_id in accounts:
        client_id, client_secret = await db.get_account_secrets(tg_id=tg_id, avito_id=avito_id)
        avito_client = AvitoAccount()
        await avito_client.set_client_id(client_id=client_id)
        await avito_client.set_client_secret(client_secret=client_secret)
        await avito_client.get_token()
        logger.info(f"Клиент успешно найден!")
        await avito_client.unsubscribe_to_notifications(server_url=server_url)
        await avito_client.close_session()

    await message.answer("Вы отписаны от всех уведомлений!")
