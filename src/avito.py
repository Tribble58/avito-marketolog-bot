import json
import logging
import aiohttp

logger = logging.getLogger(__name__)


class AvitoClient:
    """
    Implements interaction with Avito API
    """

    def __init__(self):
        self.client_id = None
        self.client_secret = None
        self.token = None
        self.avito_id = None
        self.name = None
        self.number = None
        self.session = aiohttp.ClientSession()
        self.base_url = "https://api.avito.ru"

    async def run_session(self):

        """
        Gets token and id of user in Avito
        :return: None
        """

        await self.get_token()
        await self.get_avito_id()

    async def get_token(self):
        """
        Gets token by secret keys
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
                try:
                    self.token = (await response.json())["access_token"]
                    logger.info(f"Токен получен: {self.token[:10]}...")
                except KeyError:
                    logger.error(f"Ошибка парсинга токена: {response.status} - {await response.text()}")
            else:
                logger.error(f"Ошибка получения токена: {response.status} - {await response.text()}")
        return

    async def get_client_id(self):
        """
        Getter for AVITO client id
        :return:
        """
        return self.client_id

    async def set_client_id(self, client_id):
        """
        Setter of client_id
        :param client_id:
        :return:
        """
        self.client_id = client_id

    async def get_client_secret(self):
        """
        Getter for AVITO client secret
        :return:
        """
        return self.client_secret

    async def set_client_secret(self, client_secret):
        """
        Setter of client_secret
        :param client_secret:
        :return:
        """
        self.client_secret = client_secret

    async def validate_avito_client(self):
        """
        Requests token of Avito client by given client_id and client_secret
        :return:
        """
        await self.get_token()
        if self.token:
            return True
        else:
            return False

    async def get_avito_id(self):
        """
        Gets id of user in Avito
        :return: avito_id
        """

        if not self.token:
            logger.error("Ошибка: токен не получен!")
            return

        headers = {
            "Authorization": f"Bearer {self.token}"
        }

        if not self.avito_id:
            async with self.session.get(self.base_url + "/core/v1/accounts/self", headers=headers) as response:
                if response.status == 200:
                    self.avito_id = (await response.json())["id"]
                    logger.info(f"user_id получен: {self.avito_id}")
                    return self.avito_id
                else:
                    logger.error(f"Ошибка получения user_id: {response.status} - {await response.text()}")
        else:
            return self.avito_id

    async def get_avito_client_info(self):
        """
        Gets information about Avito account
        :return:
        """

        headers = {
            "Authorization": f"Bearer {self.token}"
        }

        async with self.session.get(self.base_url + "/core/v1/accounts/self", headers=headers) as response:
            if response.status == 200:
                try:
                    result = await response.json()
                    name, number = result["name"], result["phone"]
                    logger.info(f"Имя {name} и телефон {number} для аккаунта {self.avito_id} получены!")
                    self.name, self.number = name, number
                    return self.name, self.number
                except KeyError as e:
                    logger.error(f"Ошибка получения имени или телефона: {e}")
            else:
                logger.error(
                    f"Ошибка получения имени и телефона для пользователя {self.avito_id}: {response.status} - {await response.text()}")

        return

    async def get_name(self):
        """
        Getter for AVITO client name
        :return:
        """
        return self.name

    async def set_name(self, name):
        """
        Getter for AVITO client name
        :return:
        """
        self.name = name

    async def get_number(self):
        """
        Getter for AVITO client phone number
        :return:
        """
        return self.number

    async def set_number(self, number):
        """
        Getter for AVITO client name
        :return:
        """
        self.number = number

    async def get_unread_chats(self):
        """
        Gets unread chats
        :return: chats
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
                    chats = []
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
                        chats.append({
                            "sender_id": sender_id,
                            "sender_name": sender_name,
                            "id": chat_id
                        })
                        i += 1
                        if limit == i:
                            break

                    return chats

                else:
                    logger.info("Непрочитанных чатов нет!")
            else:
                logger.error(f"Ошибка получения чатов: {response.status} - {await response.text()}")

    async def get_messages(self, chat_id):
        """
        Gets chat messages
        :return: messages
        """

        headers = {
            "Authorization": f"Bearer {self.token}"
        }

        async with self.session.get(self.base_url + f"/messenger/v3/accounts/{self.avito_id}/chats/{chat_id}/messages",
                                    headers=headers) as response:
            if response.status == 200:
                messages = (await response.json())["messages"]
                messages = []
                # Вывод последних 3 сообщений
                for k in range(3):
                    message_text = messages[k]["content"][
                        "text"]  # TODO: схема разная на разный тип отправляемого сообщения, дополнить тут впоследствии
                    messages.append(message_text)
                logger.info("Информация о чатах успешно получена!")
                return messages
            else:
                logger.error(
                    f"Ошибка получения сообщений с чатом {chat_id}: {response.status} - {await response.text()}")

    async def send_message(self, chat_id: int, message: str):
        """
        Sends message to chat
        chat_id: id of chat
        message: text of message
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

        async with self.session.post(
                self.base_url + f"/messenger/v1/accounts/{self.avito_id}/chats/{chat_id}/messages/",
                headers=headers,
                json=payload) as response:
            if response.status == 200:
                logger.info("Сообщение успешно отправлено!")
            else:
                logger.error(f"Ошибка отправки сообщения: {response.status} - {await response.text()}")

    # async def add_template(self, new_template):
    #     """
    #     Добавление нового шаблона
    #     new_template: шаблон
    #     """
    #     templates_length = len(self.templates.values())
    #     self.templates[templates_length] = new_template
    #     logger.info("Шаблон успешно добавлен!")

    # async def edit_template(self, template_id, new_template):
    #     """
    #     Изменение существующего шаблона
    #     template_id: идентификатор шаблона, ключ в словаре templates
    #     new_template: шаблон
    #     """
    #     self.templates[template_id] = new_template
    #     logger.info("Шаблон успешно изменен!")

    async def subscribe_to_notifications(self, server_url):
        """
        Sends request of subscription to notifications
        :param server_url: URL of server Avito will send notifications to
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        payload = {
            "url": server_url
        }

        async with self.session.post(self.base_url + f"/messenger/v3/webhook", headers=headers,
                                     json=payload) as response:
            if response.status == 200:
                logger.debug(f"Ответ сервера: {json.loads(await response.text())}")
                if (json.loads(await response.text()))["ok"]:
                    logger.debug(f"Пользователь подписался на уведомления клиента!")
                else:
                    logger.error("Не удалось подписаться на пользователя, сервер АВИСТО вернул ok = false")
            else:
                logger.exception(f"Ошибка подписки: {response.status} - {await response.text()}")

    async def unsubscribe_to_notifications(self, server_url):
        """
        Sends request of cancelling subscription to notifications
        :param server_url: URL of server Avito will stop sending notifications to
        :return:
        """

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        payload = {
            "url": server_url
        }

        async with self.session.post(self.base_url + f"/messenger/v1/webhook/unsubscribe", headers=headers,
                                     json=payload) as response:
            if response.status == 200:
                logger.debug(f"Ответ сервера: {json.loads(await response.text())}")
                if (json.loads(await response.text()))["ok"]:
                    logger.debug(f"Пользователь отписался на уведомления клиента!")
                else:
                    logger.error("Не удалось отписаться на пользователя, сервер АВИСТО вернул ok = false")
            else:
                logger.exception(f"Ошибка отписки: {response.status} - {await response.text()}")

    async def close_session(self):
        """
        Closes htto session
        """
        await self.session.close()
        logger.info(f"Сессия для пользователя {self.avito_id} закрыта!")
