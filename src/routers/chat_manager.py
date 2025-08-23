import logging

from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import Database

logger = logging.getLogger(__name__)

from aiogram import F, Router
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, ErrorEvent

from avito import AvitoAccount
from config import ReplyState
from callbacks import ChatsCallbackFactory, MessagesCallbackFactory, TemplateTextCallbackFactory, \
    AccountsChatsCallbackFactory

"""
Router implements logic regarding chat: getting unread messages, replying, etc.
"""

chat_manager_router = Router()
avito_service_router = Router()


@chat_manager_router.message(Command("chat_manager"))
async def get_connected_accounts(message: Message, db: Database, tg_id: int):
    """
    Gets accounts connected to user
    :param message:
    :param db:
    :param tg_id:
    :return:
    """
    accounts = await db.get_accounts(tg_id=tg_id)
    if accounts:
        builder = InlineKeyboardBuilder()
        for (avito_id,) in accounts:
            name, number = await db.get_account_info(tg_id=tg_id, avito_id=avito_id)
            builder.button(
                text=f"Аккаунт {name}",
                callback_data=AccountsChatsCallbackFactory(avito_id=avito_id)
            )
            builder.adjust(1)
            await message.answer(text="Выберите аккаунт:", reply_markup=builder.as_markup())
    else:
        await message.answer(text="Подключенных аккаунтов нет! Для подключения воспользуйтесь /accounts_manager")


@avito_service_router.callback_query(AccountsChatsCallbackFactory.filter())
async def get_account_unread_chats(callback_query: CallbackQuery, avito_account: AvitoAccount):
    """
    Gets unread chats and lists them in inline buttons
    :param callback_query:
    :param avito_account:
    :return:
    """
    avito_id = await avito_account.get_avito_id()
    chats = await avito_account.get_unread_chats()
    if chats:
        builder = InlineKeyboardBuilder()
        for chat in chats:
            builder.button(
                text=f"Чат с {chat["sender_name"]}",
                callback_data=ChatsCallbackFactory(chat_id=chat["id"], avito_id=avito_id)
            )
        # One chat per row
        builder.adjust(1)
        await callback_query.message.answer(text="Выберите чат:", reply_markup=builder.as_markup())
    else:
        await callback_query.message.answer(text=f"Непрочитанных чатов нет!")
    await callback_query.answer()


@avito_service_router.callback_query(ChatsCallbackFactory.filter())
async def display_messages(callback_query: CallbackQuery, avito_account: AvitoAccount, state: FSMContext):
    """
    Gets messages by chat and lists n last messages
    :param callback_query:
    :param avito_account:
    :return:
    """
    chat_id = callback_query.data.split(":")[2]
    messages = await avito_account.get_messages(chat_id)
    # Get avito_id for further operations in handlers that are called not from avito_router and thus can not get avito_id
    avito_id = await avito_account.get_avito_id()
    await state.update_data(avito_account=avito_account)
    logger.debug(f"Avito_id: {avito_id}")

    if messages:
        builder = InlineKeyboardBuilder()
        for message in messages:
            builder.button(
                text=f"{message}",
                callback_data=MessagesCallbackFactory(chat_id=chat_id)
            )
        # One chat per row
        builder.adjust(1)
        await callback_query.message.answer(text="Выберите сообщение:", reply_markup=builder.as_markup())
    else:
        # Impossible, but still...
        await callback_query.message.answer(text=f"Непрочитанных сообщений нет!")
    await callback_query.answer()


@chat_manager_router.callback_query(MessagesCallbackFactory.filter())
async def message_actions(callback_query: CallbackQuery, state: FSMContext):
    """
    Offers options for answering to the message
    :param callback_query:
    :param state:
    :return:
    """
    chat_id = callback_query.data.split(":")[1]
    logger.debug(f"Chat_id: {chat_id}")

    kb = [
        [InlineKeyboardButton(text="Ответить шаблонным сообщением", callback_data="choose_template_message")],
        [InlineKeyboardButton(text="Ответить другим сообщением", callback_data="create_custom_message")],
    ]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=kb,
        # Adjust button
        resize_keyboard=True
    )

    await state.update_data(chat_id=chat_id)

    await callback_query.message.answer(text="Выберите, как ответить:", reply_markup=keyboard)
    await callback_query.answer()


@chat_manager_router.callback_query(F.data == "choose_template_message")
async def choose_template_message(callback_query: CallbackQuery, db: Database):
    """
    Gets template messages from database and displays them as inline buttons
    """
    tg_id = callback_query.from_user.id
    templates = await db.get_templates(tg_id=tg_id)

    if templates:
        builder = InlineKeyboardBuilder()
        for template_text, template_id in templates:
            builder.button(
                text=f"{template_text}",
                callback_data=TemplateTextCallbackFactory(template_text=template_text)
            )
        # One chat per row
        builder.adjust(1)
        await callback_query.message.answer(text="Выберите шаблон для ответа:", reply_markup=builder.as_markup())
    else:
        await callback_query.message.answer(text="Шаблонов нет!\nПерейти к редактору шаблонов /templates_editor")
    await callback_query.answer()


@chat_manager_router.callback_query(TemplateTextCallbackFactory.filter())
async def validate_template_message(callback_query: CallbackQuery, state: FSMContext):
    """
    Validates the process of sending the template message
    :param callback_query:
    :param state:
    :return:
    """
    template_text = callback_query.data.split(":")[1]

    await state.update_data(message=template_text)

    kb = [
        [InlineKeyboardButton(text="Да, отправить данный шаблон сообщения", callback_data="send_message")],
        [InlineKeyboardButton(text="Нет, выбрать другой шаблон сообщения", callback_data="choose_template_message")],
    ]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=kb,
        # Adjust button
        resize_keyboard=True
    )

    await callback_query.message.answer(
        text=f"Вы уверены, что хотите оправить данное сообщение? \n\n\"{template_text}\"",
        reply_markup=keyboard)
    await callback_query.answer()


@chat_manager_router.callback_query(F.data == "send_message")
async def send_message(callback_query: CallbackQuery, state: FSMContext):
    """
    Sends message
    :param callback_query:
    :param state:
    :return:
    """
    chat_id = await state.get_value("chat_id")
    message = await state.get_value("message")
    # TODO: костыль, исправить как-то
    avito_account_: AvitoAccount = await state.get_value("avito_account")
    avito_account = AvitoAccount()
    await avito_account.set_client_id(client_id=(await avito_account_.get_client_id()))
    await avito_account.set_client_secret(client_secret=(await avito_account_.get_client_secret()))
    await avito_account.run_session()

    await avito_account.send_message(chat_id, message)
    await callback_query.message.answer(text=f"Сообщение \"{message}\" отправлено!")
    # TODO: сделать так, чтобы это сообщение было прочитано
    await callback_query.answer()
    # Clear chat_id and message from state
    await state.clear()
    await avito_account.close_session()


@chat_manager_router.callback_query(F.data == "create_custom_message")
async def create_custom_message(callback_query: CallbackQuery, state: FSMContext):
    """
    Waits for inserting custom message and sends it to validation
    :param callback_query:
    :param state:
    :return:
    """
    await callback_query.message.answer(text="Введите сообщение ниже:")
    await state.set_state(ReplyState.waiting_for_custom_message)
    await callback_query.answer()


@chat_manager_router.message(ReplyState.waiting_for_custom_message)
async def validate_custom_message(message: Message, state: FSMContext):
    """
    Validates custom message that user wishes to send
    :param message:
    :param state:
    :return:
    """
    message_text = message.text
    await state.update_data(message=message_text)

    builder = InlineKeyboardBuilder()

    builder.button(
        text="Да, отправить данное сообщение",
        callback_data="send_message"
    )
    builder.button(
        text="Нет, создать другое сообщение",
        callback_data="create_custom_message"
    )
    # One chat per row
    builder.adjust(1)
    await message.answer(text=f"Вы уверены, что хотите оправить данное сообщение? \n{message_text}",
                         reply_markup=builder.as_markup())


@chat_manager_router.error()
async def error_handler(event: ErrorEvent):
    """
    Global error handler for all types of errors
    :param event:
    :return:
    """
    logger.critical("Chat manager: critical error caused by %s", event.exception, exc_info=True)

    return True
