import aiohttp
import logging
from src.config import Settings

logger = logging.getLogger(__name__)


class AvitoUser:
    """
    Класс, реализующий логику взаимодействия с API Авито, а также хранящий параметры подключения и т.д.
    """

    def __init__(self):
        self.client_id = Settings.client_id
        self.client_secret = Settings.client_secret
        self.token = None
        self.avito_id = None
        self.session = aiohttp.ClientSession()
        self.base_url = "https://api.avito.ru"
        self.templates = {
            0: "Товар продан!",
            1: "Цену и остальную актуальную информацию смотрите на сайте www.xyz.ru"
        }
        logger.debug("Пользователь создан!")

    async def run_session(self):

        """
        Открывает сессию, получает токен
        :return: None
        """

        await self.get_token()
        await self.get_user_id()

    async def get_token(self):
        """
        Получение токена по переданным секретным данным
        :return: None
        """
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        async with self.session.post(self.base_url + "/token", data=payload, headers=headers) as response:
            if response.status == 200:
                self.token = (await response.json())["access_token"]
                logger.info(f"Токен получен: {self.token[:10]}...")
            else:
                logger.exception(f"Ошибка получения токена: {response.status} - {await response.text()}")
                raise Exception(f"Ошибка получения токена: {response.status} - {await response.text()}")

    async def get_user_id(self):
        """
        Получение идентификатора пользователя в Авито (user_id), который используется в последующих запросах
        :return:
        """

        if not self.token:
            logger.error("Ошибка: токен не получен!")
            raise Exception("Ошибка: токен не получен!")

        headers = {
            "Authorization": f"Bearer {self.token}"
        }

        async with self.session.get(self.base_url + "/core/v1/accounts/self", headers=headers) as response:
            if response.status == 200:
                self.avito_id = (await response.json())["id"]
                logger.info(f"user_id получен: {self.avito_id}")
            else:
                logger.exception(f"Ошибка получения user_id: {response.status} - {await response.text()}")
                raise Exception(f"Ошибка получения user_id: {response.status} - {await response.text()}")

    async def get_unread_chats(self):
        """
        Получение чатов с непрочитанными сообщениями
        :return: chats_info
        """

        headers = {
            "Authorization": f"Bearer {self.token}"
        }

        params = {
            "unread_only": "true"
        }

        async with self.session.get(self.base_url + f"/messenger/v2/accounts/{self.avito_id}/chats", headers=headers,
                                    params=params) as response:
            if response.status == 200:

                if len((await response.json())["chats"]) > 0:

                    chats_info = []
                    logger.info(f"Получено непрочитанных чатов: {len((await response.json())["chats"])}")

                    # Вывести последние 3 чата
                    limit = 3
                    i = 0
                    for chat in (await response.json())["chats"]:
                        chat_id = chat["id"]
                        for k in range(len(chat["users"])):
                            if chat["users"][k]["id"] != self.avito_id:
                                sender_id = chat["users"][k]["id"]
                                sender_name = chat["users"][k]["name"]

                        chats_info.append({
                            "sender_id": sender_id,
                            "sender_name": sender_name,
                            "id": chat_id
                        })
                        i += 1
                        if limit == i:
                            break

                    return chats_info

                else:
                    logger.info("Непрочитанных чатов нет!")

            else:
                logger.exception(f"Ошибка получения чатов: {response.status} - {await response.text()}")
                raise Exception(f"Ошибка получения чатов: {response.status} - {await response.text()}")

    async def get_unread_messages(self, chat_id):
        """
        Получение непрочитанных сообщений
        :return: messages_info
        """

        headers = {
            "Authorization": f"Bearer {self.token}"
        }

        async with self.session.get(self.base_url + f"/messenger/v3/accounts/{self.avito_id}/chats/{chat_id}/messages",
                                    headers=headers) as response:
            if response.status == 200:

                messages = (await response.json())["messages"]
                messages_info = []
                # Вывод последних 3 сообщений
                for k in range(3):
                    message_text = messages[k]["content"][
                        "text"]  # TODO: схема разная на разный тип отправляемого сообщения, дополнить тут впоследствии
                    messages_info.append(message_text)

                logger.info("Информация о чатах успешно получена!")
                return messages_info
            else:
                logger.exception(
                    f"Ошибка получения сообщений с чатом {chat_id}: {response.status} - {await response.text()}")
                raise Exception(
                    f"Ошибка получения сообщений с чатом {chat_id}: {response.status} - {await response.text()}")

    async def send_message(self, chat_id: int, message: str):
        """
        Отправка сообщения
        chat_id: идентификатор чата
        message: отправляемое сообщение
        """

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        payload = {
            "message": {
                "text": message
            },
            "type": "text"
        }

        logger.info("Сообщение успешно отправлено!")

        async with self.session.post(
                self.base_url + f"/messenger/v1/accounts/{self.avito_id}/chats/{chat_id}/messages/",
                headers=headers, json=payload) as response:
            if response.status == 200:
                logger.info("Сообщение успешно отправлено!")
            else:
                logger.exception(f"Ошибка отправки сообщения: {response.status} - {await response.text()}")
                raise Exception(f"Ошибка отправки сообщения: {response.status} - {await response.text()}")

    async def add_template(self, new_template):
        """
        Добавление нового шаблона
        new_template: шаблон
        """
        templates_length = len(self.templates.values())
        self.templates[templates_length] = new_template
        logger.info("Шаблон успешно добавлен!")

    async def edit_template(self, template_id, new_template):
        """
        Изменение существующего шаблона
        template_id: идентификатор шаблона, ключ в словаре templates
        new_template: шаблон
        """
        self.templates[template_id] = new_template
        logger.info("Шаблон успешно изменен!")

    async def close_session(self):
        """
        Закрытие HTTP-сессии
        """
        await self.session.close()
        logger.info(f"Сессия для пользователя {self.avito_id} закрыта!")
