import logging

from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.exc import IntegrityError

from callbacks import TemplatesCallbackFactory
from database import Database

logger = logging.getLogger(__name__)

from aiogram import F, Router
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, ErrorEvent

from config import ReplyState

"""
Router implements logic regarding templates: adding, delete, update operations.
"""

templates_editor_router = Router()


@templates_editor_router.message(Command("templates_editor"))
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


@templates_editor_router.callback_query(F.data == "show_templates_to_edit")
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


@templates_editor_router.callback_query(TemplatesCallbackFactory.filter())
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


@templates_editor_router.callback_query(F.data == "get_new_template_from_user")
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


@templates_editor_router.message(ReplyState.waiting_for_new_template)
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
        await db.update_template(tg_id=tg_id, template_id=int(template_id), new_template=new_template)
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


@templates_editor_router.callback_query(F.data == "delete_template")
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


@templates_editor_router.error()
async def global_error_handler(event: ErrorEvent):
    """
    Error handler for all types of errors
    :param event:
    :return:
    """
    logger.critical("Templates_editor: critical error caused by %s", event.exception, exc_info=True)

    return True
