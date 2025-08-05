import logging

from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.exc import IntegrityError

from callbacks import TemplatesCallbackFactory
from src.database import Database

logger = logging.getLogger(__name__)

from aiogram import F, Router
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

from src.avito import AvitoAccount
from src.config import ReplyState
from src.callbacks import ChatsCallbackFactory, MessagesCallbackFactory, TemplateTextCallbackFactory, \
    AccountsCallbackFactory, AccountsChatsCallbackFactory

"""
This main bot implements basic logic of User interaction with its Accounts.
All available commands are presented in the menu and in /start command.

Glossary:
    User is a person who manages several accounts, user is always considered in the Telegram context.
    Account is a client (shop, private person, seller, etc) that provides any kind of services in Avito and pays User for
    his/her account promotion.
"""

# commands_router = Router()
router = Router()
avito_router = Router()


@router.message(Command("start"))
async def start(message: Message):
    """
    Start message with menu.
    """
    logger.debug("Стартовая команда")

    await message.answer(
        "Привет! Выбери команды из списка кнопки Меню, или введи команду вручную. Вот список команд:\n\n"
        "/get_unread_messages - 🍌Получить непрочитанные чаты\n"
        "/templates_editor - 🥭Открыть редактор шаблонов\n"
        "/accounts_manager - 🍉Открыть управление аккаунтами\n"
        "/support - 🍏Связаться с поддержкой\n"
        "/something - ⚙️Че-то")


@router.message(Command("accounts_manager"))
async def accounts_manager(message: Message):
    """
    Account manager module that is responsible for user interactions with managed Avito accounts
    :param message:
    :return:
    """
    kb = [
        [InlineKeyboardButton(text="Все аккаунты", callback_data="list_accounts")],
        [InlineKeyboardButton(text="Подключить аккаунт", callback_data="wait_for_account_secrets")],
    ]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=kb,
        # Adjust button
        resize_keyboard=True
    )

    await message.answer(text="Что сделать?", reply_markup=keyboard)


@router.callback_query(F.data == "wait_for_account_secrets")
async def wait_for_account_secrets(callback_query: CallbackQuery, state: FSMContext):
    """
    Waits for user input and sends it to validation
    :param callback_query:
    :param state:
    :return:
    """
    await callback_query.message.answer(text="Введите client_id и client_secret аккаунта, который хотите подключить.\n"
                                             "Формат ввода: client_id:client_secret\n"
                                             "Пример: 54AZwJISvjVDasqDC13:ZzRUHTgoHMo5MtooCRuEIoa48Nv3pha12f23evwqq")
    await state.set_state(ReplyState.waiting_for_account_secrets)
    await callback_query.answer()


@router.message(ReplyState.waiting_for_account_secrets)
async def validate_connect_account(message: Message, state: FSMContext):
    """
    Checks that client with provided secret keys exists in Avito, gets his info and displays to user
    :param message:
    :param state:
    :return:
    """
    client_id, client_secret = message.text.split(":")[0], message.text.split(":")[1]

    avito_account = AvitoAccount()
    await avito_account.set_client_id(client_id=client_id)
    await avito_account.set_client_secret(client_secret=client_secret)
    if not await avito_account.validate_avito_account():
        await message.answer("Аккаунта не существует! Проверьте client_id и client_secret и попробуйте заново!")

    await avito_account.run_session()
    name, number = await avito_account.get_avito_account_info()
    await avito_account.set_name(name=name)
    await avito_account.set_number(number=number)

    kb = [
        [InlineKeyboardButton(text="Да, подключить аккаунт", callback_data="connect_account")],
    ]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=kb,
        # Adjust button
        resize_keyboard=True
    )

    await message.answer(text="Вы уверены, что хотите добавить данный аккаунт?\n"
                              f"Имя аккаунта: {name}\n"
                              f"Телефон: {number}\n",
                         reply_markup=keyboard)
    await state.update_data(avito_account=avito_account)


@router.callback_query(F.data == "connect_account")
async def connect_account(callback_query: CallbackQuery, db: Database, state: FSMContext):
    """
    Connects account to user
    :param callback_query:
    :param db:
    :param state:
    :return:
    """
    tg_id = callback_query.from_user.id
    avito_account: AvitoAccount = await state.get_value("avito_account")
    avito_id = await avito_account.get_avito_id()
    name, number, client_id, client_secret = (await avito_account.get_name(),
                                              await avito_account.get_number(),
                                              await avito_account.get_client_id(),
                                              await avito_account.get_client_secret())

    await db.insert_account(tg_id=tg_id, avito_id=avito_id, name=name, number=number, client_id=client_id,
                            client_secret=client_secret)
    await callback_query.message.answer(text="Аккаунт успешно добавлен!\n"
                                             "К управлению аккаунтами /accounts_manager")
    await callback_query.answer()
    await state.clear()


@router.callback_query(F.data == "list_accounts")
async def list_accounts(callback_query: CallbackQuery, db: Database):
    """
    Lists all available account that user connected
    :param callback_query:
    :param db:
    :return:
    """
    tg_id = callback_query.from_user.id
    accounts = await db.get_accounts(tg_id=tg_id)

    if accounts:
        builder = InlineKeyboardBuilder()
        for (avito_id,) in accounts:
            name, number = await db.get_account_info(tg_id=tg_id, avito_id=avito_id)
            builder.button(
                text=f"Имя аккаунта: {name}, номер: {number}",
                callback_data=AccountsCallbackFactory(avito_id=avito_id)
            )
        # One account per row
        builder.adjust(1)
        await callback_query.message.answer(text="Выберите аккаунт:", reply_markup=builder.as_markup())
    else:
        await callback_query.message.answer(text=f"Нет подключенных аккаунтов!")

    await callback_query.answer()


@router.callback_query(AccountsCallbackFactory.filter())
async def account_edit_options(callback_query: CallbackQuery, state: FSMContext):
    """
    Provides edit options for accounts: disconnect, etc
    :param state:
    :param callback_query:
    :return:
    """
    avito_id = int(callback_query.data.split(":")[1])

    kb = [
        [InlineKeyboardButton(text="Отключить аккаунт", callback_data="disconnect_account")],
    ]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=kb,
        # Adjust button
        resize_keyboard=True
    )
    await callback_query.message.answer("Выберите действие:", reply_markup=keyboard)
    await state.update_data(avito_id=avito_id)

@router.callback_query(F.data == "disconnect_account")
async def disconnect_account(callback_query: CallbackQuery, db: Database, state: FSMContext):
    """
    Disconnects account from user
    :param callback_query:
    :param db:
    :return:
    """
    tg_id = callback_query.from_user.id
    avito_id = await state.get_value("avito_id")

    await db.delete_account(tg_id=tg_id, avito_id=avito_id)
    await callback_query.message.answer(text=f"Аккаунт успешно удален!")

    await callback_query.answer()


@router.message(Command("support"))
async def support(message: Message, ):
    """
    Auxiliary command for connecting admins
    :param message:
    :return:
    """
    await message.answer(text="Здесь будет модуль взаимодействия с поддержкой")


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


@router.message(Command("get_unread_messages"))
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


@avito_router.callback_query(AccountsChatsCallbackFactory.filter())
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


@avito_router.callback_query(ChatsCallbackFactory.filter())
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


@router.callback_query(MessagesCallbackFactory.filter())
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


@router.callback_query(F.data == "choose_template_message")
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


@router.callback_query(TemplateTextCallbackFactory.filter())
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


@router.message(Command("templates_editor"))
async def edit_templates(message: Message):
    """
    Templates editor module that implements modifying template messages
    :param message:
    :return:
    """
    kb = [
        [InlineKeyboardButton(text="Показать все шаблоны", callback_data="show_templates_to_edit")],
        [InlineKeyboardButton(text="Создать новый шаблон", callback_data="get_new_template_from_user")],
    ]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=kb,
        # Adjust button
        resize_keyboard=True
    )
    await message.answer(text="Выберите действие:", reply_markup=keyboard)


@router.callback_query(F.data == "show_templates_to_edit")
async def show_templates_to_edit(callback_query: CallbackQuery, db: Database):
    """
    Gets template messages user has and displays them as inline buttons for user to choose which template to edit
    :param callback_query:
    :param db:
    :return:
    """
    tg_id = callback_query.from_user.id
    templates = await db.get_templates(tg_id=tg_id)

    if templates:
        builder = InlineKeyboardBuilder()
        for template_text, template_id in templates:
            builder.button(
                text=f"{template_text}",
                callback_data=TemplatesCallbackFactory(template_id=template_id)  # TODO: почему то кидает на валидацию
            )

        # One chat per row
        builder.adjust(1)
        await callback_query.message.answer(text="Для изменения шаблона выберите один из вариантов ниже:",
                                            reply_markup=builder.as_markup())
    else:
        await callback_query.message.answer(text="Шаблонов нет!\nПерейти к редактору шаблонов /templates_editor")
    await callback_query.answer()


@router.callback_query(TemplatesCallbackFactory.filter())
async def edit_options(callback_query: CallbackQuery, state: FSMContext):
    """

    :param state:
    :param callback_query:
    :return:
    """
    template_id = callback_query.data.split(":")[1]
    await state.update_data(template_id=template_id)
    kb = [
        [InlineKeyboardButton(text="Изменить шаблона", callback_data="get_new_template_from_user")],
        [InlineKeyboardButton(text="Удалить шаблон", callback_data="delete_template")],
    ]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=kb,
        # Adjust button
        resize_keyboard=True
    )
    await callback_query.message.answer(text="Выберите действие:", reply_markup=keyboard)


@router.callback_query(F.data == "get_new_template_from_user")
async def get_new_template_from_user(callback_query: CallbackQuery, state: FSMContext):
    """
    Waits for user to insert new template
    :param callback_query:
    :param state:
    :return:
    """
    # if callback_query.data != 'get_new_template_from_user':
    #     # Add template id to state if template is to be updated further
    #     template_id = int(callback_query.data.split('|')[-1])
    #     await state.update_data(template_id=template_id)

    await callback_query.message.answer(text="Введите новый шаблон:")
    await state.set_state(ReplyState.waiting_for_new_template)
    await callback_query.answer()


@router.message(ReplyState.waiting_for_new_template)
async def create_new_template(message: Message, state: FSMContext, db: Database):
    """
    Inserts new template to the database
    :param message:
    :param state:
    :param db:
    :return:
    """
    tg_id = message.from_user.id
    new_template = message.text

    template_id = await state.get_value("template_id")

    # Update template if template_id is not None else add new template
    if template_id:
        await db.update_template(tg_id=tg_id, template_id=template_id, new_template=new_template)
        await message.answer(text="Шаблон успешно изменен!\nК редактору шаблонов /templates_editor")
    else:
        try:
            await db.add_template(tg_id=tg_id, new_template=new_template)
            await message.answer(text="Шаблон успешно создан!\nК редактору шаблонов /templates_editor")
        except IntegrityError as e:
            logger.error(f"{e}")
            await db.close()
            await message.answer(text="Для добавления шаблона сначала нажмите /start!")

    await state.clear()


@router.callback_query(F.data == "delete_template")
async def delete_template(callback_query: CallbackQuery, state: FSMContext, db: Database):
    """
    Inserts new template to the database
    :param callback_query:
    :param state:
    :param db:
    :return:
    """
    tg_id = callback_query.from_user.id

    template_id = int(await state.get_value("template_id"))
    await db.delete_template(tg_id=tg_id, template_id=template_id)
    await callback_query.message.answer(text="Шаблон успешно удален!\nК редактору шаблонов /templates_editor")
    await state.clear()


@router.callback_query(F.data == "create_custom_message")
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


@router.message(ReplyState.waiting_for_custom_message)
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


@router.callback_query(F.data == "send_message")
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
    await callback_query.answer()
    # Clear chat_id and message from state
    await state.clear()
    await avito_account.close_session()


@router.message()
async def process_other_text_answers(message: Message):
    """
    Processes messages sent to Telegram that do not fit in any filters
    :param message:
    :return:
    """
    await message.answer("Для начала работы введите /start или выберите нужную команду из списка Меню")
