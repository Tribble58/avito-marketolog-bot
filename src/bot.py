import logging

from aiogram.utils.keyboard import InlineKeyboardBuilder

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s - [%(levelname)s] -  %(name)s"
                           "- (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s")
logger = logging.getLogger(__name__)

import asyncio
from aiogram import F, Bot, Dispatcher
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, BotCommand

from src.avito import AvitoClient
from src.config import ReplyState, Settings
from src.callbacks import ChatsCallbackFactory

tg_bot = Bot(token=Settings.bot_token)

dp = Dispatcher()

user_sessions = {}


async def set_menu_commands(bot: Bot):
    """
    Задает меню бота для навигации.
    """
    logger.debug("Создание меню...")
    await bot.set_my_commands(
        commands=
        [
            BotCommand(command="get_unread_messages", description="🍌Получить непрочитанные чаты"),
            BotCommand(command="template_editor", description="🥭Редактор шаблонов"),
            BotCommand(command="accounts_manager", description="🍉Управление аккаунтами"),
            BotCommand(command="support", description="🍏Поддержка"),
        ]
    )
    logger.debug("Меню создано!")


@dp.message(Command("start"))
async def start(message: Message):
    """
    Начальная команда.
    Регистрирует пользователя в сессиях.
    """
    logger.debug("Стартовая команда")
    user_id = message.from_user.id
    avito_client = AvitoClient(telegram_user_id=user_id)
    if user_id not in user_sessions:
        logger.debug("Пользователь не в сессиях")
        user_sessions[user_id] = avito_client
        logger.debug("Пользователь зарегистрирован в сессиях!")

    await avito_client.run_session()

    await message.answer(
        "Привет! Выбери команды из списка кнопки Меню, или введи команду вручную. Вот список команд:\n\n"
        "/get_unread_messages - 🍌Получить непрочитанные чаты\n"
        "/template_editor - 🥭Открыть редактор шаблонов\n"
        "/accounts_manager - 🍉Открыть управление аккаунтами\n"
        "/support - 🍏Связаться с поддержкой")


@dp.message(Command("accounts_manager"))
async def accounts_manager(message: Message):
    user_id = message.from_user.id
    avito_client = user_sessions.get(user_id)
    if not avito_client:
        logger.debug("Пользователь не в сессиях")
        await message.answer("Для начала работы введите /start")
        return
    await message.answer(text="Здесь можно будет добавить аккаунт, удалить аккаунт и т.д.")


@dp.message(Command("support"))
async def support(message: Message):
    user_id = message.from_user.id
    avito_client = user_sessions.get(user_id)
    if not avito_client:
        await message.answer("Для начала работы введите /start")
        return
    await message.answer(text="Здесь будет модуль взаимодействия с поддержкой")


@dp.callback_query(F.data == 'something')
async def dummy(callback_query: CallbackQuery):
    await callback_query.message.answer(text="Отдыхай, кнопка в разработке... TUNG TUNG TUNG SAHUR")
    await callback_query.answer()


@dp.message(Command("get_unread_messages"))
async def get_unread_chats(message: Message):
    """
    Выводит чаты в инлайн кнопках.
    """
    user_id = message.from_user.id
    avito_client = user_sessions.get(user_id)
    if not avito_client:
        await message.answer("Для начала работы введите /start")
        return

    chats_info = await avito_client.get_unread_chats_info()

    if isinstance(chats_info, list):
        builder = InlineKeyboardBuilder()
        for chat in chats_info:
            builder.button(
                text=f"Чат с {chat["sender_name"]}",
                callback_data=ChatsCallbackFactory(chat_id=chat["id"])
            )
        builder.adjust(1)
        await message.answer(text="Выберите чат:", reply_markup=builder.as_markup())
    else:
        await message.answer(text=f"{chats_info}")


@dp.callback_query(ChatsCallbackFactory.filter())
async def display_unread_messages(callback_query: CallbackQuery):
    """
    Выводит непрочитанные сообщения в инлайн кнопках.
    """
    user_id = callback_query.from_user.id
    avito_client = user_sessions.get(user_id)
    if not avito_client:
        await callback_query.message.answer("Сначала воспользуйтесь /start.")
        return
    chat_id = callback_query.data.split(":")[1]

    messages_info = await avito_client.get_unread_messages(chat_id)

    kb = [[InlineKeyboardButton(text=f"{messages_info[k]}", callback_data=f"message_{chat_id}")]
          for k in range(len(messages_info))]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=kb,
        # Adjust button
        resize_keyboard=True,
    )

    await callback_query.message.answer(text="Выберите сообщение для ответа:", reply_markup=keyboard)
    await callback_query.answer()


@dp.callback_query(F.data.startswith("message_"))
async def message_actions(callback_query: CallbackQuery, state: FSMContext):
    """
    Выводит опции ответа.
    """
    chat_id = callback_query.data.split("_")[1]

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


@dp.callback_query(F.data == "choose_template_message")
async def choose_template_message(callback_query: CallbackQuery):
    """
    Выводит инлайн кнопки шаблонов сообщений.
    Ведет на редактор шаблонов.
    """
    user_id = callback_query.from_user.id
    avito_client = user_sessions.get(user_id)
    if not avito_client:
        await callback_query.message.answer("Сначала воспользуйтесь /start.")
        return
    template_messages = avito_client.templates

    kb = []
    for key, value in template_messages.items():
        kb.append([InlineKeyboardButton(text=value, callback_data=f"validate_template_message_{key}")])
    kb.append([InlineKeyboardButton(text="Редактор шаблонов", callback_data="template_editor")])

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=kb,
        # Adjust button
        resize_keyboard=True
    )

    await callback_query.message.answer(text="Выберите шаблон для ответа:", reply_markup=keyboard)
    await callback_query.answer()


@dp.callback_query(F.data.startswith("validate_template_message_"))
async def validate_template_message(callback_query: CallbackQuery, state: FSMContext):
    """
    Валидация отправления шаблона сообщения.
    """
    user_id = callback_query.from_user.id
    avito_client = user_sessions.get(user_id)
    if not avito_client:
        await callback_query.message.answer("Сначала воспользуйтесь /start.")
        return
    template_messages = avito_client.templates
    template_id = int(callback_query.data.split('_')[-1])
    template_message = template_messages[template_id]

    await state.update_data(message=template_message)

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
        text=f"Вы уверены, что хотите оправить данное сообщение? \n\n\"{template_message}\"",
        reply_markup=keyboard)
    await callback_query.answer()


@dp.message(Command("template_editor"))
async def edit_templates(message: Message):
    """
    Редактор шаблонов.
    """

    kb = [
        [InlineKeyboardButton(text="Редактировать существующий шаблон", callback_data=f"show_templates_to_edit")],
        [InlineKeyboardButton(text="Создать новый шаблон", callback_data=f"get_new_template_from_user")],
    ]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=kb,
        # Adjust button
        resize_keyboard=True
    )
    await message.answer(text="Выберите действие:", reply_markup=keyboard)


@dp.callback_query(F.data == "show_templates_to_edit")
async def show_templates_to_edit(callback_query: CallbackQuery):
    """
    Отображение шаблонов для изменения.
    """
    user_id = callback_query.from_user.id
    avito_client = user_sessions.get(user_id)
    if not avito_client:
        await callback_query.message.answer("Сначала воспользуйтесь /start.")
        return
    template_messages = avito_client.templates

    kb = []
    for key, value in template_messages.items():
        kb.append([InlineKeyboardButton(text=value, callback_data=f"get_new_template_from_user_{key}")])

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=kb,
        # Adjust button
        resize_keyboard=True
    )

    await callback_query.message.answer(text="Выберите шаблон для изменения:", reply_markup=keyboard)
    await callback_query.answer()


@dp.callback_query(F.data.startswith("get_new_template_from_user"))
async def get_new_template_from_user(callback_query: CallbackQuery, state: FSMContext):
    """
    Получение нового шаблона от пользователя.
    """
    user_id = callback_query.from_user.id
    avito_client = user_sessions.get(user_id)
    if not avito_client:
        await callback_query.message.answer("Сначала воспользуйтесь /start.")
        return
    if callback_query.data == 'get_new_template_from_user':
        pass
    else:
        template_id = int(callback_query.data.split('_')[-1])
        await state.update_data(template_id=template_id)

    await callback_query.message.answer(text="Введите новый шаблон:")
    await state.set_state(ReplyState.waiting_for_new_template)
    await callback_query.answer()


@dp.message(ReplyState.waiting_for_new_template)
async def create_new_template(message: Message, state: FSMContext):
    """
    Изменение шаблона.
    """
    user_id = message.from_user.id
    avito_client = user_sessions.get(user_id)
    if not avito_client:
        await message.answer("Сначала воспользуйтесь /start.")
        return

    new_template = message.text

    if await state.get_value("template_id") is not None:
        # Update template
        template_id = await state.get_value("template_id")
        await avito_client.edit_template(template_id, new_template)
        user_sessions[user_id] = avito_client
        await message.answer(text="Шаблон успешно изменен!")
    else:
        # Insert new template
        await avito_client.add_template(new_template)
        user_sessions[user_id] = avito_client
        await message.answer(text="Шаблон успешно добавлен!")

    await state.clear()


@dp.callback_query(F.data.startswith("create_custom_message"))
async def create_custom_message(callback_query: CallbackQuery, state: FSMContext):
    """
    Ожидание кастомного сообщение от пользователя.
    """
    await callback_query.message.answer(text="Введите сообщение ниже:")
    await state.set_state(ReplyState.waiting_for_custom_message)
    await callback_query.answer()


@dp.message(ReplyState.waiting_for_custom_message)
async def validate_custom_message(message: Message, state: FSMContext):
    """
    Валидация кастомного сообщение от пользователя.
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


@dp.callback_query(F.data.startswith("send_message"))
async def send_message(callback_query: CallbackQuery, state: FSMContext):
    """
    Отправка сообщения.
    """
    user_id = callback_query.from_user.id
    avito_client = user_sessions.get(user_id)
    if not avito_client:
        await callback_query.message.answer("Сначала воспользуйтесь /start.")
        return
    chat_id = await state.get_value("chat_id")
    message = await state.get_value("message")

    await state.clear()

    await avito_client.send_message(chat_id, message)
    await callback_query.message.answer(text=f"Сообщение \"{message}\" отправлено!")
    await callback_query.answer()


@dp.message()
async def process_other_text_answers(message: Message):
    """
    Обработка сообщений, не касающихся основных команд.
    """
    user_id = message.from_user.id
    avito_client = user_sessions.get(user_id)
    if not avito_client:
        await message.answer("Для начала работы введите /start")
    else:
        await message.answer("Для начала работы введите /start или выберите нужную команду из списка Меню")


async def run_bot():
    """
    Запускает поллинг, задает меню.
    """

    await set_menu_commands(tg_bot)
    # Пропуск апдейтов, которые были отправлены во время отключения бота
    await tg_bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(tg_bot)


async def shutdown():
    """
    Закрывает HTTP-сессии для каждого пользователя.
    """
    print("Shutting down. Closing sessions...")

    for client in user_sessions.values():
        await client.close_session()
    print("All sessions are closed.")


if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        asyncio.run(shutdown())
