"""WebSocket endpoints for real-time triage queue updates and per-user events."""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import jwt
from jwt.exceptions import InvalidTokenError

from app.config import settings
from app.utils.auth import COOKIE_NAME

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


class QueueConnectionManager:
    """Manages active WebSocket connections for triage queue broadcasts."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.add(ws)
        logger.info("WebSocket client connected. Total: %d", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)
        logger.info("WebSocket client disconnected. Total: %d", len(self._connections))

    async def broadcast(self, data: dict) -> None:
        """Send JSON payload to every connected client, dropping broken connections."""
        payload = json.dumps(data)
        stale: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_text(payload)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self._connections.discard(ws)


class UserConnectionManager:
    """Per-user WebSocket connections for targeted push (e.g. reminders)."""

    def __init__(self) -> None:
        self._by_user: dict[str, set[WebSocket]] = {}

    async def connect(self, user_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._by_user.setdefault(user_id, set()).add(ws)

    def disconnect(self, user_id: str, ws: WebSocket) -> None:
        conns = self._by_user.get(user_id)
        if conns is None:
            return
        conns.discard(ws)
        if not conns:
            self._by_user.pop(user_id, None)

    def connection_count(self, user_id: str) -> int:
        return len(self._by_user.get(user_id, set()))

    async def send_to_user(self, user_id: str, data: dict) -> int:
        """Send to all connections for a user. Returns delivered count."""
        conns = self._by_user.get(user_id)
        if not conns:
            return 0
        payload = json.dumps(data)
        stale: list[WebSocket] = []
        delivered = 0
        for ws in conns:
            try:
                await ws.send_text(payload)
                delivered += 1
            except Exception:
                stale.append(ws)
        for ws in stale:
            conns.discard(ws)
        if not conns:
            self._by_user.pop(user_id, None)
        return delivered


queue_manager = QueueConnectionManager()
user_manager = UserConnectionManager()


def _decode_ws_token(token: str | None) -> str | None:
    """Return the sub claim (user_id) if valid, else None."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except InvalidTokenError:
        return None
    sub = payload.get("sub")
    return sub if isinstance(sub, str) else None


def _validate_ws_token(token: str | None) -> bool:
    return _decode_ws_token(token) is not None


@router.websocket("/ws/triage-queue")
async def triage_queue_ws(
    ws: WebSocket,
    token: str = Query(default=None),
) -> None:
    """WebSocket endpoint for triage queue updates.

    Requires a valid JWT `token` query param for authentication.
    Rejects unauthenticated connections with close code 4001.
    """
    if not _validate_ws_token(token):
        await ws.close(code=4001)
        return

    await queue_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        queue_manager.disconnect(ws)


@router.websocket("/ws/user")
async def user_events_ws(
    ws: WebSocket,
    token: str = Query(default=None),
) -> None:
    """Per-user event stream (medication reminders, notifications).

    The connection is scoped to the token's subject claim; events published
    to that user's Redis channel are forwarded to every active connection.
    Authenticates from the access_token cookie, then the `token` query
    param as a fallback for non-browser clients.
    """
    user_id = _decode_ws_token(ws.cookies.get(COOKIE_NAME)) or _decode_ws_token(token)
    if user_id is None:
        await ws.close(code=4001)
        return

    await user_manager.connect(user_id, ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        user_manager.disconnect(user_id, ws)
