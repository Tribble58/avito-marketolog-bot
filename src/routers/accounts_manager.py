import logging

logger = logging.getLogger(__name__)

from aiogram import F, Router

from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, ErrorEvent
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from config import ReplyState
from database import Database
from callbacks import AccountsCallbackFactory

from avito import AvitoAccount

"""
Router implements logic regarding accounts: connection, disconnection, update, etc.
"""

accounts_manager_router = Router()

# TODO: add check account before adding

@accounts_manager_router.message(Command("accounts_manager"))
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


@accounts_manager_router.callback_query(F.data == "list_accounts")
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


@accounts_manager_router.callback_query(AccountsCallbackFactory.filter())
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


@accounts_manager_router.callback_query(F.data == "disconnect_account")
async def disconnect_account(callback_query: CallbackQuery, db: Database, state: FSMContext):
    """
    Disconnects account from user
    :param state:
    :param callback_query:
    :param db:
    :return:
    """
    tg_id = callback_query.from_user.id
    avito_id = await state.get_value("avito_id")

    await db.delete_account(tg_id=tg_id, avito_id=avito_id)
    await callback_query.message.answer(text=f"Аккаунт успешно удален!")

    await callback_query.answer()


@accounts_manager_router.callback_query(F.data == "wait_for_account_secrets")
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


@accounts_manager_router.message(ReplyState.waiting_for_account_secrets)
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


@accounts_manager_router.callback_query(F.data == "connect_account")
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


@accounts_manager_router.error()
async def error_handler(event: ErrorEvent):
    """
    Error handler for all types of errors
    :param event:
    :return:
    """
    logger.critical("Accounts manager: error caused by %s", event.exception, exc_info=True)

    return True
