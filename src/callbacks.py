from sys import prefix

from aiogram.filters.callback_data import CallbackData


class ChatsCallbackFactory(CallbackData, prefix="chat"):
    chat_id: str
