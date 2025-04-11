from aiogram import F, Router
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

from avito import AvitoClient
from config import ReplyState

router = Router()

user_sessions = {}


@router.message(Command("start"))
async def start(message: Message):
    """
    Начальная команда.
    Регистрирует пользователя в сессиях.
    :param message:
    """
    user_id = message.from_user.id
    avito_client = AvitoClient(telegram_user_id=user_id)
    if user_id not in user_sessions:
        user_sessions[user_id] = avito_client

    await avito_client.run_session()

    kb = [
        [InlineKeyboardButton(text="Получить непрочитанные чаты", callback_data='get_unread_messages')],
        [InlineKeyboardButton(text="Еще что-то (в разработке)", callback_data='something')],
    ]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=kb,
        # Adjust button
        resize_keyboard=True
        # Hide button when pressed
    )
    await message.answer("Привет! Что сделать?", reply_markup=keyboard)


@router.callback_query(F.data == 'something')
async def dummy(callback_query: CallbackQuery):
    await callback_query.message.answer(text="Отдыхай, кнопка в разработке... TUNG TUNG TUNG SAHUR")
    await callback_query.answer()


@router.callback_query(F.data == "get_unread_messages")
async def get_unread_chats(callback_query: CallbackQuery):
    """
    Выводит чаты в инлайн кнопках.
    """
    user_id = callback_query.from_user.id
    avito_client = user_sessions.get(user_id)
    if not avito_client:
        await callback_query.message.answer("Сначала воспользуйтесь /start.")
        return

    chats_info = await avito_client.get_unread_chats_info()

    if isinstance(chats_info, list):

        kb = [[InlineKeyboardButton(text=f"Чат с {chat["sender_name"]}", callback_data=f"chat_{chat["id"]}")]
              for chat in chats_info]
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=kb,
            # Adjust button
            resize_keyboard=True,
        )
        await callback_query.message.answer(text="Выберите чат:", reply_markup=keyboard)
        await callback_query.answer()
    else:
        await callback_query.message.answer(text=f"{chats_info}")


@router.callback_query(F.data.startswith("chat_"))
async def display_unread_messages(callback_query: CallbackQuery):
    """
    Выводит непрочитанные сообщения в инлайн кнопках.
    """
    user_id = callback_query.from_user.id
    avito_client = user_sessions.get(user_id)
    if not avito_client:
        await callback_query.message.answer("Сначала воспользуйтесь /start.")
        return
    chat_id = callback_query.data.split("_")[1]

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


@router.callback_query(F.data.startswith("message_"))
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


@router.callback_query(F.data == "choose_template_message")
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
    kb.append([InlineKeyboardButton(text="Редактор шаблонов", callback_data=f"template_editor")])

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=kb,
        # Adjust button
        resize_keyboard=True
    )

    await callback_query.message.answer(text="Выберите шаблон для ответа:", reply_markup=keyboard)
    await callback_query.answer()


@router.callback_query(F.data.startswith("validate_template_message_"))
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


@router.callback_query(F.data == "template_editor")
async def edit_templates(callback_query: CallbackQuery):
    """
    Редактор шаблонов.
    """
    user_id = callback_query.from_user.id
    avito_client = user_sessions.get(user_id)
    if not avito_client:
        await callback_query.message.answer("Сначала воспользуйтесь /start.")
        return
    kb = [
        [InlineKeyboardButton(text="Редактировать существующий шаблон", callback_data=f"show_templates_to_edit")],
        [InlineKeyboardButton(text="Создать новый шаблон", callback_data=f"get_new_template_from_user")],
    ]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=kb,
        # Adjust button
        resize_keyboard=True
    )
    await callback_query.message.answer(text="Выберите действие:",
                                        reply_markup=keyboard)
    await callback_query.answer()


@router.callback_query(F.data == "show_templates_to_edit")
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


@router.callback_query(F.data.startswith("get_new_template_from_user"))
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


@router.message(ReplyState.waiting_for_new_template)
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


@router.callback_query(F.data.startswith("create_custom_message"))
async def create_custom_message(callback_query: CallbackQuery, state: FSMContext):
    """
    Ожидание кастомного сообщение от пользователя.
    """
    await callback_query.message.answer(text="Введите сообщение ниже:")
    await state.set_state(ReplyState.waiting_for_custom_message)
    await callback_query.answer()


@router.message(ReplyState.waiting_for_custom_message)
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
    await state.clear()


@router.callback_query(F.data.startswith("send_message"))
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

    await avito_client.send_message(chat_id, message)
    await callback_query.message.answer(text=f"Сообщение \"{message}\" отправлено!")
    await callback_query.answer()
