from aiogram.fsm.state import StatesGroup, State
from dotenv import load_dotenv
import os

load_dotenv()


class Settings:
    """
    Класс для хранения чувствительной информации, которая располагается в .env.
    Для авторизации API Авито использует идентификатор и секретный ключ клиента, который можно получить при оформлении
    базового тарифа
    """
    client_id: str = os.getenv("AVITO_CLIENT_ID")
    client_secret: str = os.getenv("AVITO_CLIENT_SECRET")
    bot_token: str = os.getenv("TG_BOT_TOKEN")

class ReplyState(StatesGroup):
    """
    Класс состояний ожидания ввода сообщений от пользователя
    """
    waiting_for_new_template = State()
    waiting_for_custom_message = State()