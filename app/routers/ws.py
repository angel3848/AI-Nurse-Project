"""WebSocket endpoint for real-time triage queue updates."""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import jwt
from jwt.exceptions import InvalidTokenError

from app.config import settings

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


queue_manager = QueueConnectionManager()


def _validate_ws_token(token: str | None) -> bool:
    """Validate a JWT token for WebSocket connections. Returns True if valid."""
    if not token:
        return False
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload.get("sub") is not None
    except InvalidTokenError:
        return False


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
