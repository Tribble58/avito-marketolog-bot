import logging

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s - [%(levelname)s] -  %(name)s"
                           "- (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s")
logger = logging.getLogger(__name__)
from pytest import fixture, mark
from sqlalchemy import inspect

from src.database import Database

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@fixture
async def db():
    """
    Starts SQLite database, closes session after finish
    :return:
    """
    db = Database(db_url=TEST_DB_URL)
    await db.init_models()
    yield db

    # Close database session at the end
    await db.close()


@mark.asyncio
async def test_check_tables(db: Database):
    """
    Tests that all necessary tables are created
    :param db:
    :return:
    """
    async with db.engine.connect() as conn:
        tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())

    expected_tables = {"users", "accounts", "users_templates"}
    assert set(tables) == expected_tables


@mark.asyncio
async def test_insert_user(db: Database):
    """
    Tests that User is inserted
    :param db:
    :return:
    """
    await db.insert_user(123)
    user_id = await db.get_user_id(123)
    assert user_id is not None


@mark.asyncio
async def test_insert_account(db: Database):
    """
    Tests that account is inserted
    :param db:
    :return:
    """
    await db.insert_user(123)
    await db.insert_account(123, 999, "test_name", "test_phone_number", "test_client_id", "test_client_secret")
    assert await db.get_avito_id(123) == 999
    assert await db.get_accounts(123) == [(999,)]
    assert await db.get_account_info(123, 999) == [("test_name", "test_phone_number",)]
    assert await db.get_account_secrets(123, 999) == [("test_client_id", "test_client_secret",)]

@mark.asyncio
async def test_delete_account(db: Database):
    await db.insert_user(123)
    await db.insert_account(123, 999, "test_name", "test_phone_number", "test_client_id", "test_client_secret")
    await db.delete_account(123, 999)
    assert await db.get_avito_id(123) is None


@mark.asyncio
async def test_template_crud(db: Database):
    await db.insert_user(123)
    await db.add_template(123, "hello!")
    templates = await db.get_templates(123)
    assert len(templates) == 1

    template_id = templates[0][1]
    await db.update_template(123, template_id, "updated")
    updated_templates = await db.get_templates(123)
    assert updated_templates[0][0] == "updated"
