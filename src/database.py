import logging
from typing import Tuple, List

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.config import Settings
from src.models import Base, User, UserTemplate, Account

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_url: str = Settings.db_connection_uri):
        self.engine = create_async_engine(db_url)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self._session: AsyncSession | None = None

    async def init_models(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Таблицы созданы!")

    async def get_session(self) -> AsyncSession:
        """
        Gets session from factory if not created
        :return:
        """
        if self._session is None:
            self._session = self.session_factory()
            logger.debug("Session is get from factory!")
        return self._session

    async def get_user_id(self, tg_id: int) -> int | None:
        """
        Gets id of user from users table
        :param tg_id:
        :return: user_id:int | None
        """
        session = await self.get_session()
        result = await session.execute(
            select(User.id).select_from(User).where(User.tg_id == tg_id)
        )
        user_id = result.scalar_one_or_none()

        if user_id:
            return user_id
        else:
            logger.info(f"User {tg_id} does not exist.")

    async def insert_user(self, tg_id: int) -> None:
        """
        Adds new user to users table
        :param tg_id: 
        :return: None
        """
        session = await self.get_session()

        # Check that user does not exist 
        user_id = await self.get_user_id(tg_id=tg_id)
        if user_id:
            logger.debug(f"User {tg_id} already exists!")
            return

        user = User(tg_id=tg_id)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info(f"Added new user {tg_id} to database!")

    async def get_avito_id(self, tg_id: int) -> int | None:
        """
        Gets avito_id of user from users table
        :param tg_id: 
        :return: 
        """
        session = await self.get_session()
        user_id = await self.get_user_id(tg_id=tg_id)
        result = await session.execute(
            select(Account.avito_id)
            .select_from(Account)
            .where(Account.user_id == user_id)
        )
        avito_user_id = result.scalar_one_or_none()

        if avito_user_id:
            return avito_user_id
        else:
            logger.info(f"No corresponding account for user {tg_id}!")

    async def get_account_id(self, tg_id: int, avito_id: int) -> int | None:
        """
        Gets id of account from accounts table
        :param tg_id: id of user in users table
        :param avito_id: id of client in AVITO
        :return: int | None
        """
        session = await self.get_session()
        user_id = await self.get_user_id(tg_id=tg_id)
        result = await session.execute(
            select(Account.id)
            .select_from(Account)
            .where(
                (Account.user_id == user_id)
                & (Account.avito_id == avito_id)
            )
        )
        account_id = result.scalar_one_or_none()
        return account_id

    async def insert_account(self, tg_id: int, avito_id: int, name: str, number: str, client_id: str,
                             client_secret: str) -> None:
        """
        Adds account to accounts table
        :param tg_id: id of user in users table
        :param avito_id: id of client in AVITO
        :param number: name of client in AVITO
        :param name: phone number of client in AVITO
        :param client_id: client_id of client in AVITO
        :param client_secret: client_secret of client in AVITO
        :return:
        """
        session = await self.get_session()

        # Check that client does not exist
        account_id = await self.get_account_id(tg_id=tg_id, avito_id=avito_id)
        if account_id:
            logger.debug(f"Account {avito_id} of user {tg_id} already exists!")
            return

        user_id = await self.get_user_id(tg_id=tg_id)
        account = Account(user_id=user_id, avito_id=avito_id, name=name, number=number, client_id=client_id,
                          client_secret=client_secret)
        session.add(account)
        await session.commit()
        await session.refresh(account)
        logger.info(f"Added new account {avito_id} for user {tg_id} to database!")

    async def get_accounts(self, tg_id: int) -> List[int]:
        """
        Gets Avito accounts connected to provided User id
        :param tg_id:
        :return:
        """
        session = await self.get_session()
        user_id = await self.get_user_id(tg_id=tg_id)
        result = await session.execute(
            select(Account.avito_id)
            .select_from(Account)
            .where(Account.user_id == user_id)
        )
        accounts = result.fetchall()
        return accounts

    async def get_account_info(self, tg_id: int, avito_id: int) -> List[Tuple[str, str]]:
        """
        Gets Avito account info (name, phone number, etc.)
        :param tg_id:
        :param avito_id:
        :return:
        """
        session = await self.get_session()
        user_id = await self.get_user_id(tg_id=tg_id)
        result = await session.execute(
            select(
                Account.name,
                Account.number
            )
            .select_from(Account)
            .where(
                (Account.user_id == user_id)
                & (Account.avito_id == avito_id)
            )
        )
        account_info = result.one_or_none()
        return account_info

    async def delete_account(self, tg_id: int, avito_id: int) -> None:
        """
        Deletes account
        :param tg_id:
        :param avito_id:
        :return:
        """
        session = await self.get_session()
        user_id = await self.get_user_id(tg_id=tg_id)
        await session.execute(
            delete(Account).where(
                (Account.user_id == user_id)
                & (Account.avito_id == avito_id))
        )
        await session.commit()

    async def get_account_secrets(self, tg_id: int, avito_id: int) -> List[Tuple[str, str]]:
        """
        Gets client secret ids and keys
        :param tg_id:
        :param avito_id:
        :return:
        """

        session = await self.get_session()
        user_id = await self.get_user_id(tg_id=tg_id)
        result = await session.execute(
            select(
                Account.client_id,
                Account.client_secret
            )
            .select_from(Account)
            .where(
                (Account.user_id == user_id)
                & (Account.avito_id == avito_id)
            )
        )
        secrets = result.one_or_none()
        return secrets

    async def get_tg_id_by_account(self, avito_id: int) -> int | None:
        """
        Gets id of user in Telegram by user`s client
        :param avito_id:
        :return: tg_id:
        """
        session = await self.get_session()
        user_id = select(Account.user_id).where(Account.avito_id == avito_id).scalar_subquery()
        logger.debug(f"user_id: {user_id}")
        result = await session.execute(
            select(User.tg_id)
            .select_from(User)
            .where(User.id == user_id)
        )
        tg_id = result.scalar_one_or_none()
        return tg_id

    async def get_templates(self, tg_id: int) -> List[Tuple[str, int]]:
        """
        Gets templates of user from users_templates table
        :param tg_id:
        :return:
        """
        logger.info(f"Getting templates for user {tg_id}...")
        session = await self.get_session()
        user_id = await self.get_user_id(tg_id=tg_id)
        result = await session.execute(
            select(
                UserTemplate.template,
                UserTemplate.id
            )
            .select_from(UserTemplate)
            .where(UserTemplate.user_id == user_id)
        )
        templates = result.fetchall()
        return templates

    async def add_template(self, tg_id: int, new_template: str) -> None:
        """
        Adds template to users_templates table
        :param tg_id:
        :param new_template:
        :return:
        """
        session = await self.get_session()
        user_id = select(User.id).where(User.tg_id == tg_id).scalar_subquery()
        template = UserTemplate(user_id=user_id, template=new_template)
        session.add(template)
        await session.commit()
        logger.info(f"Template for {tg_id} has been added!")

    async def update_template(self, tg_id: int, template_id: int, new_template: str) -> None:
        """
        Updates template of user in users_templates table
        :param tg_id:
        :param template_id:
        :param new_template:
        :return:
        """
        session = await self.get_session()
        user_id = select(User.id).where(User.tg_id == tg_id).scalar_subquery()
        await session.execute(
            update(UserTemplate)
            .where(
                (UserTemplate.user_id == user_id) &
                (UserTemplate.id == template_id)
            )
            .values(template=new_template)
        )
        await session.commit()
        logger.info(f"Template for {tg_id} has been updated!")

    async def delete_template(self, tg_id: int, template_id: int) -> None:
        """
        Deletes template in users_templates table
        :param tg_id:
        :param template_id:
        :return:
        """
        session = await self.get_session()
        user_id = select(User.id).where(User.tg_id == tg_id).scalar_subquery()
        await session.execute(
            delete(UserTemplate).where(
                (UserTemplate.user_id == user_id)
                & (UserTemplate.id == template_id)
            )
        )
        await session.commit()
        logger.info(f"Template {template_id} for {tg_id} has been deleted!")

    async def close(self) -> None:
        """
        Closes session
        :return:
        """
        if self._session is not None:
            await self._session.close()
            self._session = None
            logger.info("Session is closed!")
