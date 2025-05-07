import logging

from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.exc import IntegrityError

from src.database import Database

logger = logging.getLogger(__name__)

from aiogram import F, Router
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

from src.avito import AvitoAccount
from src.config import ReplyState
from src.callbacks import ChatsCallbackFactory, MessagesCallbackFactory, TemplatesCallbackFactory, \
    AccountsCallbackFactory

"""
This main bot implements basic logic of User interaction with its Accounts.
All available commands are presented in the menu and in /start command.

Glossary:
    User is a person who manages several accounts, user is always considered in the Telgram context.
    Account is a client (shop, private person, seller, etc) that provides any kind of services in Avito and pays User for
    his/her account promotion.
"""

commands_router = Router()
router = Router()


@commands_router.message(Command("start"))
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


@commands_router.message(Command("accounts_manager"))
async def accounts_manager(message: Message):
    """
    Account manager module that is responsible for user interactions with managed Avito accounts
    :param message:
    :return:
    """
    kb = [
        [InlineKeyboardButton(text="Подключить аккаунт", callback_data="wait_for_client_secrets")],
        [InlineKeyboardButton(text="Отключить аккаунт", callback_data="list_accounts")],
    ]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=kb,
        # Adjust button
        resize_keyboard=True
    )

    await message.answer(text="Что сделать?", reply_markup=keyboard)
    # TODO: сделать чтобы кнопка не светилась после нажатия


@router.callback_query(F.data == "wait_for_client_secrets")
async def wait_for_client_secrets(callback_query: CallbackQuery, state: FSMContext):
    """
    Waits for user input and sends it to validation
    :param callback_query:
    :param state:
    :return:
    """
    await callback_query.message.answer(text="Введите client_id и client_secret аккаунта, который хотите подключить.\n"
                                             "Формат ввода: client_id:client_secret\n"
                                             "Пример: 54AZwJISvjVDasqDC13:ZzRUHTgoHMo5MtooCRuEIoa48Nv3pha12f23evwqq")
    await state.set_state(ReplyState.waiting_for_client_secrets)


@router.message(ReplyState.waiting_for_client_secrets)
async def validate_connect_account(message: Message, state: FSMContext):
    """
    Checks that client with provided secret keys exists in Avito, gets his info and displays to user
    :param message:
    :param state:
    :return:
    """
    client_id, client_secret = message.text.split(":")[0], message.text.split(":")[1]

    avito_client = AvitoAccount()
    await avito_client.set_client_id(client_id=client_id)
    await avito_client.set_client_secret(client_secret=client_secret)
    if not await avito_client.validate_avito_client():
        await message.answer("Аккаунта не существует! Проверьте client_id и client_secret и попробуйте заново!")

    await avito_client.run_session()
    name, number = await avito_client.get_avito_client_info()
    await avito_client.set_name(name=name)
    await avito_client.set_number(number=number)

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
    await state.update_data(avito_client=avito_client)


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
    avito_client: AvitoAccount = await state.get_value("avito_client")
    avito_id = await avito_client.get_avito_id()
    name, number, client_id, client_secret = (await avito_client.get_name(),
                                              await avito_client.get_number(),
                                              await avito_client.get_client_id(),
                                              await avito_client.get_client_secret())

    await db.insert_account(tg_id=tg_id, avito_id=avito_id, name=name, number=number, client_id=client_id,
                            client_secret=client_secret)
    await callback_query.message.answer(text="Аккаунт успешно добавлен!\n"
                                             "К управлению аккаунтами /accounts_manager")


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
        for avito_id in accounts:
            name, number = await db.get_account_info(tg_id=tg_id, avito_id=avito_id)
            builder.button(
                text=f"Имя аккаунта: {name},"
                     f"номер: {number}",
                callback_data=AccountsCallbackFactory(avito_id=avito_id)
            )
        # One account per row
        builder.adjust(1)
        await callback_query.message.answer(text="Выберите аккаунт:", reply_markup=builder.as_markup())
    else:
        await callback_query.message.answer(text=f"Нет подключенных аккаунтов!")


@router.callback_query(AccountsCallbackFactory.filter())
async def disconnect_account(callback_query: CallbackQuery, db: Database):
    """
    Disconnects account from user
    :param callback_query:
    :param db:
    :return:
    """
    tg_id = callback_query.from_user.id
    avito_id = int(callback_query.data.split(":")[1])

    await db.delete_account(tg_id=tg_id, avito_id=avito_id)
    await callback_query.message.answer(text=f"Аккаунт успешно удален!")


@commands_router.message(Command("support"))
async def support(message: Message, user_sessions: dict):
    """
    Auxiliary command for connecting admins
    :param message:
    :param user_sessions:
    :return:
    """
    user_id = message.from_user.id
    avito_client = user_sessions.get(user_id)
    if not avito_client:
        await message.answer("Для начала работы введите /start")
        return
    await message.answer(text="Здесь будет модуль взаимодействия с поддержкой")


@commands_router.message(Command("something"))
async def dummy(callback_query: CallbackQuery, db: Database):
    """
    Dummy
    :param callback_query:
    :param db:
    :return:
    """
    # user_id = callback_query.from_user.id
    # await db.add_tg_user(telegram_id=user_id)
    await callback_query.answer(text="Отдыхай, кнопка в разработке... TUNG TUNG TUNG SAHUR")
    # await callback_query.answer()


@router.message(Command("get_unread_messages"))
async def get_unread_chats(message: Message, avito_client: AvitoAccount):
    """
    Gets unread chats and lists them in inline buttons
    :param message:
    :param avito_client:
    :return:
    """
    chats = await avito_client.get_unread_chats()

    if chats:
        builder = InlineKeyboardBuilder()
        for chat in chats:
            builder.button(
                text=f"Чат с {chat["sender_name"]}",
                callback_data=ChatsCallbackFactory(chat_id=chat["id"])
            )
        # One chat per row
        builder.adjust(1)
        await message.answer(text="Выберите чат:", reply_markup=builder.as_markup())
    else:
        await message.answer(text=f"Непрочитанных чатов нет!")


@router.callback_query(ChatsCallbackFactory.filter())
async def display_messages(callback_query: CallbackQuery, avito_user: AvitoAccount):
    """
    Gets messages by chat and lists n last messages
    :param callback_query:
    :param avito_user:
    :return:
    """
    chat_id = callback_query.data.split(":")[1]

    messages = await avito_user.get_messages(chat_id)

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

    kb = [
        [InlineKeyboardButton(text="Ответить шаблонным сообщением", callback_data=f"choose_template_message")],
        [InlineKeyboardButton(text="Ответить другим сообщением", callback_data=f"create_custom_message")],
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
                callback_data=TemplatesCallbackFactory(template_text=template_text)
            )
        # One chat per row
        builder.adjust(1)
        await callback_query.message.answer(text="Выберите шаблон для ответа:", reply_markup=builder.as_markup())
    else:
        await callback_query.message.answer(text=f"Шаблонов нет!\nПерейти к редактору шаблонов /templates_editor")
    await callback_query.answer()


@router.callback_query(TemplatesCallbackFactory.filter())
async def validate_template_message(callback_query: CallbackQuery, state: FSMContext):
    """
    Validates sending the template message
    :param callback_query:
    :param state:
    :return:
    """

    template_text = callback_query.data.split(":")[1]

    await state.update_data(message=template_text)

    kb = [
        [InlineKeyboardButton(text="Да, отправить данный шаблон сообщения", callback_data=f"send_message")],
        [InlineKeyboardButton(text="Нет, выбрать другой шаблон сообщения", callback_data=f"choose_template_message")],
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
        [InlineKeyboardButton(text="Создать новый шаблон", callback_data="get_new_template_from_user")],
        [InlineKeyboardButton(text="Редактировать существующий шаблон", callback_data="show_templates_to_edit")],
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

    kb = []
    # for key, value in template_messages.items():
    for template_text, template_id in templates:
        kb.append([InlineKeyboardButton(text=template_text,
                                        # No need to replace it with callback factory because it leads to the same point
                                        # another handler has
                                        callback_data=f"get_new_template_from_user|{template_id}"
                                        )
                   ]
                  )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=kb,
        # Adjust button
        resize_keyboard=True
    )

    await callback_query.message.answer(text="Выберите шаблон для изменения:", reply_markup=keyboard)
    await callback_query.answer()


@router.callback_query(F.data.startswith("get_new_template_from_user"))
async def get_new_template_from_user(callback_query: CallbackQuery, state: FSMContext):
    """
    Waits for user to insert new template
    :param callback_query:
    :param state:
    :return:
    """
    if callback_query.data != 'get_new_template_from_user':
        # Add template id to state if template is to be updated further
        template_id = int(callback_query.data.split('|')[-1])
        await state.update_data(template_id=template_id)

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


@router.callback_query(F.data.startswith("create_custom_message"))
async def create_custom_message(callback_query: CallbackQuery, state: FSMContext):
    """
    Waits for inserting custom message and sends it to validation
    :param callback_query:
    :param state:
    :return:
    """
    await callback_query.message.answer(text="Введите сообщение ниже:")
    await state.set_state(ReplyState.waiting_for_custom_message)
    # await callback_query.answer()


@router.message(ReplyState.waiting_for_custom_message)
async def validate_custom_message(message: Message, state: FSMContext):
    """
    Validates custom message that user wishes to send
    :param message:
    :param state:
    :return:
    """
    await state.update_data(message=message.text)

    kb = [
        [InlineKeyboardButton(text="Да, отправить данное сообщение", callback_data=f"send_message")],
        [InlineKeyboardButton(text="Нет, создать другое сообщение", callback_data=f"create_custom_message")],
    ]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=kb,
        # Adjust button
        resize_keyboard=True
    )
    await message.answer(text=f"Вы уверены, что хотите оправить данное сообщение? \n{message.text}",
                         reply_markup=keyboard)


@router.callback_query(F.data == "send_message")
async def send_message(callback_query: CallbackQuery, state: FSMContext, avito_user: AvitoAccount):
    """
    Sends message
    :param callback_query:
    :param state:
    :param avito_user:
    :return:
    """

    chat_id = await state.get_value("chat_id")
    message = await state.get_value("message")

    await avito_user.send_message(chat_id, message)
    # Clear chat_id and message from state
    await state.clear()
    await callback_query.message.answer(text=f"Сообщение \"{message}\" отправлено!")
    await callback_query.answer()


@router.message()
async def process_other_text_answers(message: Message, user_sessions: dict):
    """
    Processes messages sent to Telegram that do not fit in any filters
    :param message:
    :param user_sessions:
    :return:
    """
    user_id = message.from_user.id
    avito_client = user_sessions.get(user_id)
    if not avito_client:
        await message.answer("Для начала работы введите /start")
    else:
        await message.answer("Для начала работы введите /start или выберите нужную команду из списка Меню")
