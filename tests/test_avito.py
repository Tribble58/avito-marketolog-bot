from aioresponses import aioresponses
from pytest import fixture, mark
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.avito import AvitoAccount


@fixture()
async def avito_account():
    account = AvitoAccount()
    account.client_id = "test_id"
    account.client_secret = "test_secret"
    return account


@mark.asyncio
async def test_get_token(avito_account):
    expected_token = "some-token"

    with aioresponses() as m:
        m.post(
            "https://api.avito.ru/token",
            payload={"access_token": expected_token},
            status=200
        )

        await avito_account.get_token()
        await avito_account.close_session()

        assert avito_account.token == expected_token


@mark.asyncio
async def test_get_avito_id_no_token(avito_account):
    avito_account.token = None
    result = await avito_account.get_avito_id()
    assert result is None


@mark.asyncio
async def test_get_avito_id(avito_account):
    avito_account.token = "some-token"
    expected_avito_id = 42

    with aioresponses() as m:
        m.get(
            avito_account.base_url + "/core/v1/accounts/self",
            payload={"id": expected_avito_id},
            status=200
        )

        await avito_account.get_avito_id()
        await avito_account.close_session()

        assert avito_account.id == expected_avito_id


@mark.asyncio
async def test_validate_avito_client_success(avito_account):
    expected_token = "some-token"

    with aioresponses() as m:
        m.post(
            "https://api.avito.ru/token",
            payload={"access_token": expected_token},
            status=200
        )

        is_valid = await avito_account.validate_avito_account()
        await avito_account.close_session()

        assert is_valid is True
        assert avito_account.token == expected_token


@mark.asyncio
async def test_get_avito_client_info(avito_account):
    avito_account.token = "some-token"
    avito_account.id = 123
    expected_name = "Test User"
    expected_phone = "+79000000000"

    with aioresponses() as m:
        m.get(
            "https://api.avito.ru/core/v1/accounts/self",
            payload={"name": expected_name, "phone": expected_phone},
            status=200
        )

        name, phone = await avito_account.get_avito_account_info()
        await avito_account.close_session()

        assert name == expected_name
        assert phone == expected_phone
        assert avito_account.name == expected_name
        assert avito_account.phone_number == expected_phone


@mark.asyncio
async def test_subscribe_to_notifications(avito_account):
    avito_account.token = "some-token"
    server_url = "https://example.com/webhook"

    with aioresponses() as m:
        m.post(
            "https://api.avito.ru/messenger/v3/webhook",
            payload={"ok": True},
            status=200
        )

        await avito_account.subscribe_to_notifications(server_url)
        await avito_account.close_session()


@mark.asyncio
async def test_unsubscribe_to_notifications(avito_account):
    avito_account.token = "some-token"
    server_url = "https://example.com/webhook"

    with aioresponses() as m:
        m.post(
            "https://api.avito.ru/messenger/v1/webhook/unsubscribe",
            payload={"ok": True},
            status=200
        )

        await avito_account.unsubscribe_to_notifications(server_url)
        await avito_account.close_session()


@mark.asyncio
async def test_get_unread_chats(avito_account):
    avito_account.token = "some-token"
    avito_account.id = 123
    chat_response = {
        "chats": [
            {
                "id": 42,
                "users": [
                    {"id": 123, "name": "Owner"},
                    {"id": 456, "name": "User A"}
                ]
            },
            {
                "id": 43,
                "users": [
                    {"id": 123, "name": "Owner"},
                    {"id": 789, "name": "User B"}
                ]
            }
        ]
    }

    with aioresponses() as m:
        m.get(
            f"https://api.avito.ru/messenger/v2/accounts/{avito_account.id}/chats?unread_only=true",
            payload=chat_response,
            status=200
        )

        chats = await avito_account.get_unread_chats()
        await avito_account.close_session()

        assert isinstance(chats, list)
        assert len(chats) == 2
        assert chats[0]["sender_name"] == "User A"
        assert chats[1]["sender_id"] == 789


@mark.asyncio
async def test_get_messages(avito_account):
    avito_account.token = "some-token"
    avito_account.id = 123
    chat_id = 42
    message_response = {
        "messages": [
            {"content": {"text": "Hello"}},
            {"content": {"text": "How are you?"}},
            {"content": {"text": "Bye"}}
        ]
    }

    with aioresponses() as m:
        m.get(
            f"https://api.avito.ru/messenger/v3/accounts/{avito_account.id}/chats/{chat_id}/messages",
            payload=message_response,
            status=200
        )

        messages = await avito_account.get_messages(chat_id)
        await avito_account.close_session()

        assert messages == ["Hello", "How are you?", "Bye"]


@mark.asyncio
async def test_send_message(avito_account):
    avito_account.token = "some-token"
    avito_account.id = 123
    chat_id = 42
    message = "Test message"

    with aioresponses() as m:
        m.post(
            f"https://api.avito.ru/messenger/v1/accounts/{avito_account.id}/chats/{chat_id}/messages/",
            status=200
        )

        await avito_account.send_message(chat_id, message)
        await avito_account.close_session()
