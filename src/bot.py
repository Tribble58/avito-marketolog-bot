import logging

from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.exc import IntegrityError

from callbacks import TemplatesCallbackFactory
from src.database import Database

logger = logging.getLogger(__name__)

from aiogram import F, Router
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, ErrorEvent

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
    await message.answer(text="Для обратной связи, предложений и пожеланий принимаем сообщения на почту bibaboba98@yandex.ru")


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
        [InlineKeyboardButton(text="Изменить шаблон", callback_data="get_new_template_from_user")],
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

    template_id = int(await state.get_value("template_id"))

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
