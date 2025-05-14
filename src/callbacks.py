from aiogram.filters.callback_data import CallbackData


class ChatsCallbackFactory(CallbackData, prefix="chat"):
    avito_id: int
    chat_id: str


class MessagesCallbackFactory(CallbackData, prefix="message"):
    chat_id: str


class TemplatesCallbackFactory(CallbackData, prefix="template"):
    template_text: str


class AccountsCallbackFactory(CallbackData, prefix="avito_id"):
    avito_id: int


class AccountsMessagesCallbackFactory(CallbackData, prefix="account_chats"):
    avito_id: int
