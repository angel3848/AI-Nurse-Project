import pytest
from fastapi.testclient import TestClient

from tests.conftest import create_test_user


def test_ws_connect_with_valid_token(client: TestClient, db):
    """WebSocket connection succeeds with a valid JWT token."""
    user = create_test_user(db, role="nurse")
    from app.utils.auth import create_access_token

    token = create_access_token(user.id, user.role)

    with client.websocket_connect(f"/ws/triage-queue?token={token}") as ws:
        # Connection accepted — send a message and close
        ws.close()


def test_ws_reject_without_token(client: TestClient):
    """WebSocket connection is rejected without a token."""
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/triage-queue") as ws:
            ws.receive_text()


def test_ws_reject_with_invalid_token(client: TestClient):
    """WebSocket connection is rejected with an invalid JWT."""
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/triage-queue?token=invalid.jwt.token") as ws:
            ws.receive_text()


def test_ws_broadcast(client: TestClient, db):
    """Broadcast sends data to connected clients."""
    user = create_test_user(db, role="nurse")
    from app.utils.auth import create_access_token

    token = create_access_token(user.id, user.role)

    from app.routers.ws import queue_manager

    with client.websocket_connect(f"/ws/triage-queue?token={token}") as ws:
        import asyncio

        loop = asyncio.new_event_loop()
        loop.run_until_complete(queue_manager.broadcast({"event": "queue_updated"}))
        loop.close()

        data = ws.receive_json()
        assert data["event"] == "queue_updated"
