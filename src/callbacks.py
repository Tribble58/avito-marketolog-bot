from aiogram.filters.callback_data import CallbackData


class ChatsCallbackFactory(CallbackData, prefix="chat"):
    chat_id: str

class MessagesCallbackFactory(CallbackData, prefix="message"):
    chat_id: str

class TemplatesCallbackFactory(CallbackData, prefix="template"):
    template_text: str

class AccountsCallbackFactory(CallbackData, prefix="number"):
    number: str

class AccountsCallbackFactory(CallbackData, prefix="number"):
    number: str