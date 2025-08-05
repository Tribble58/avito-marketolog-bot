from aiogram.filters.callback_data import CallbackData


class ChatsCallbackFactory(CallbackData, prefix="chat"):
    avito_id: int
    chat_id: str


class MessagesCallbackFactory(CallbackData, prefix="message"):
    chat_id: str


class TemplateTextCallbackFactory(CallbackData, prefix="template_text"):
    template_text: str


class TemplatesCallbackFactory(CallbackData, prefix="template"):
    template_id: int


class AccountsCallbackFactory(CallbackData, prefix="avito_id"):
    avito_id: int


class AccountsChatsCallbackFactory(CallbackData, prefix="account_chats"):
    avito_id: int


class CustomMessageCallbackFactory(CallbackData, prefix="custom_message"):
    avito_id: int
