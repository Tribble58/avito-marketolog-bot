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
    notifications_bot_token: str = os.getenv("TG_BOT_NOTIFICATIONS_TOKEN")
    db_host: str = os.getenv("PG_HOST")
    db_port: str = os.getenv("PG_PORT")
    db_name: str = os.getenv("PG_DATABASE")
    db_user: str = os.getenv("PG_USER")
    db_password: str = os.getenv("PG_PASSWORD")
    db_connection_uri: str = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


class ReplyState(StatesGroup):
    """
    Класс состояний ожидания ввода сообщений от пользователя
    """
    waiting_for_client_secrets: State = State()
    waiting_for_new_template: State = State()
    waiting_for_custom_message: State = State()
