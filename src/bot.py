import logging

logger = logging.getLogger(__name__)

from aiogram import Router
from aiogram.filters.command import Command
from aiogram.types import CallbackQuery, Message, ErrorEvent

"""
This main bot implements basic logic of User interaction with its Accounts.
All available commands are presented in the menu and in /start command.

Glossary:
    User is a person who manages several accounts, user is always considered in the Telegram context.
    Account is a client (shop, private person, seller, etc) that provides any kind of services in Avito and pays User for
    his/her account promotion.
"""

router = Router()


@router.message(Command("start"))
async def start(message: Message):
    """
    Start message with menu.
    """
    logger.debug("Стартовая команда")

    await message.answer(
        "Привет! Выбери команды из списка кнопки Меню, или введи команду вручную. Вот список команд:\n\n"
        "/chat_manager - ▫️Непрочитанные сообщения\n"
        "/templates_editor - ▫️Открыть редактор шаблонов\n"
        "/accounts_manager - ▫️Открыть управление аккаунтами\n"
        "/support - ▫️Связаться с поддержкой\n"
        # "/something - ⚙️Че-то"
    )


@router.message(Command("support"))
async def support(message: Message):
    """
    Auxiliary command for connecting admins
    :param message:
    :return:
    """
    await message.answer(
        text="Для обратной связи, предложений и пожеланий принимаем сообщения на почту bibaboba98@yandex.ru")


@router.message(Command("something"))
async def dummy(callback_query: CallbackQuery):
    """
    Dummy
    :param callback_query:
    :return:
    """
    # user_id = callback_query.from_user.id
    # await db.add_tg_user(telegram_id=user_id)
    await callback_query.answer(text="Отдыхай, кнопка в разработке... TUNG TUNG TUNG SAHUR")
    # await callback_query.answer()


@router.message()
async def process_other_text_answers(message: Message):
    """
    Processes messages sent to Telegram that do not fit in any filters
    :param message:
    :return:
    """
    await message.answer("Для начала работы введите /start или выберите нужную команду из списка Меню")


@router.error()
async def global_error_handler(event: ErrorEvent):
    """
    Global error handler for all types of errors
    :param event:
    :return:
    """
    logger.critical("Critical error caused by %s", event.exception, exc_info=True)

    return True
