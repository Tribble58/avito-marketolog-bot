import logging
from typing import Tuple, List

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.config import Settings
from src.models import Base, User, UserTemplate

logger = logging.getLogger(__name__)


class PostgresDatabase:
    def __init__(self, db_url: str = Settings.db_connection_uri):
        self.engine = create_async_engine(db_url)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self._session: AsyncSession | None = None

    async def init_models(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def get_session(self) -> AsyncSession:
        """
        Gets session from factory if not created
        :return:
        """
        if self._session is None:
            self._session = self.session_factory()
            logger.debug("Session is get from factory!")
        return self._session

    async def get_user_id(self, tg_id):
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

    async def set_user(self, tg_id: int):
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
        logger.info(f"Added new user {tg_id} to database.")

    async def get_avito_id(self, tg_id):
        """
        Gets avito_id of user from users table
        :param tg_id: 
        :return: 
        """
        session = await self.get_session()
        result = await session.execute(
            select(User.avito_id)
            .select_from(User)
            .where(User.tg_id == tg_id)
        )
        avito_user_id = result.scalar_one_or_none()

        if avito_user_id:
            return avito_user_id
        else:
            logger.info(f"User {tg_id} has no AVITO id!")

    async def set_avito_id(self, tg_id, avito_id):
        """
        Updates user avito_id field of users table
        :param tg_id:
        :param avito_id:
        :return:
        """
        session = await self.get_session()
        await session.execute(
            update(User)
            .where(User.tg_id == tg_id)
            .values(avito_id=avito_id)
        )
        await session.commit()
        # await session.refresh(user)

        logger.info(f"Added AVITO id to user {tg_id}!")

    async def get_templates(self, tg_id: int) -> List[Tuple[str, int]]:
        """
        Gets templates of user from users_templates table
        :param tg_id:
        :return:
        """
        logger.info(f"Getting templates for user {tg_id}...")
        session = await self.get_session()
        result = await session.execute(
            select(
                UserTemplate.template,
                UserTemplate.id
            )
            .select_from(UserTemplate)
            .where(UserTemplate.user_id == User.id)
        )
        templates = result.fetchall()
        return templates

    async def add_template(self, tg_id, new_template):
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

    async def update_template(self, tg_id, template_id, new_template):
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

    async def close(self):
        """
        Closes session
        :return:
        """
        if self._session is not None:
            await self._session.close()
            self._session = None
            logger.info("Session is closed!")
