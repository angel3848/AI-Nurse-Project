import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.ws import UserConnectionManager, user_manager
from app.services.event_bus import channel_for, publish_user_event
from tests.conftest import auth_header, create_test_user


class TestUserConnectionManager:
    @pytest.mark.asyncio
    async def test_connect_registers_under_user(self):
        mgr = UserConnectionManager()
        ws = MagicMock()

        async def accept():
            return None

        ws.accept = MagicMock(return_value=accept())
        await mgr.connect("user-1", ws)
        assert mgr.connection_count("user-1") == 1

    @pytest.mark.asyncio
    async def test_disconnect_removes_and_cleans_up(self):
        mgr = UserConnectionManager()
        ws = MagicMock()
        ws.accept = MagicMock(return_value=_async_none())
        await mgr.connect("user-1", ws)
        mgr.disconnect("user-1", ws)
        assert mgr.connection_count("user-1") == 0
        assert "user-1" not in mgr._by_user

    @pytest.mark.asyncio
    async def test_disconnect_unknown_user_is_noop(self):
        mgr = UserConnectionManager()
        mgr.disconnect("ghost", MagicMock())  # should not raise

    @pytest.mark.asyncio
    async def test_send_to_user_delivers_payload(self):
        mgr = UserConnectionManager()
        ws = MagicMock()
        ws.accept = MagicMock(return_value=_async_none())
        ws.send_text = MagicMock(return_value=_async_none())
        await mgr.connect("user-1", ws)

        delivered = await mgr.send_to_user("user-1", {"type": "ping"})
        assert delivered == 1
        sent_payload = ws.send_text.call_args.args[0]
        assert json.loads(sent_payload) == {"type": "ping"}

    @pytest.mark.asyncio
    async def test_send_to_user_with_no_connections(self):
        mgr = UserConnectionManager()
        assert await mgr.send_to_user("nobody", {"type": "ping"}) == 0

    @pytest.mark.asyncio
    async def test_send_drops_broken_connections(self):
        mgr = UserConnectionManager()
        ok_ws = MagicMock()
        ok_ws.accept = MagicMock(return_value=_async_none())
        ok_ws.send_text = MagicMock(return_value=_async_none())

        broken_ws = MagicMock()
        broken_ws.accept = MagicMock(return_value=_async_none())
        broken_ws.send_text = MagicMock(side_effect=RuntimeError("boom"))

        await mgr.connect("user-1", ok_ws)
        await mgr.connect("user-1", broken_ws)

        delivered = await mgr.send_to_user("user-1", {"x": 1})
        assert delivered == 1
        assert mgr.connection_count("user-1") == 1


def _async_none():
    async def _inner():
        return None

    return _inner()


class TestPublishUserEvent:
    def test_publish_uses_user_channel(self):
        fake_client = MagicMock()
        with patch("app.services.event_bus.redis.Redis.from_url", return_value=fake_client):
            publish_user_event("user-abc", {"type": "medication_reminder", "id": "r1"})
        fake_client.publish.assert_called_once()
        channel, payload = fake_client.publish.call_args.args
        assert channel == channel_for("user-abc")
        assert json.loads(payload) == {"type": "medication_reminder", "id": "r1"}
        fake_client.close.assert_called_once()

    def test_publish_swallows_redis_failure(self):
        with patch("app.services.event_bus.redis.Redis.from_url", side_effect=RuntimeError("down")):
            publish_user_event("user-abc", {"x": 1})  # must not raise


class TestUserEventsWebSocket:
    def test_rejects_without_token(self, client):
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/user"):
                pass

    def test_rejects_invalid_token(self, client):
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/user?token=not-a-jwt"):
                pass

    def test_accepts_valid_token_and_registers_user(self, db):
        user = create_test_user(db)
        token = auth_header(user)["Authorization"].split()[1]
        user_manager._by_user.clear()
        with TestClient(app) as ws_client:
            with ws_client.websocket_connect(f"/ws/user?token={token}"):
                assert user_manager.connection_count(user.id) == 1
        assert user_manager.connection_count(user.id) == 0

    def test_accepts_cookie_auth(self, db):
        user = create_test_user(db)
        token = auth_header(user)["Authorization"].split()[1]
        user_manager._by_user.clear()
        with TestClient(app) as ws_client:
            ws_client.cookies.set("access_token", token)
            with ws_client.websocket_connect("/ws/user"):
                assert user_manager.connection_count(user.id) == 1
        assert user_manager.connection_count(user.id) == 0
