"""Per-user event pub/sub over Redis.

Celery tasks publish synchronously; the FastAPI process runs a single
async subscriber task that fans out events to connected WebSocket clients.
"""

import json
import logging
from typing import Awaitable, Callable

import redis
import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

USER_EVENT_CHANNEL_PREFIX = "user-events:"


def channel_for(user_id: str) -> str:
    return f"{USER_EVENT_CHANNEL_PREFIX}{user_id}"


def publish_user_event(user_id: str, event: dict) -> None:
    """Sync publish to a user's event channel. Safe to call from Celery."""
    try:
        client = redis.Redis.from_url(settings.redis_url)
        try:
            client.publish(channel_for(user_id), json.dumps(event))
        finally:
            client.close()
    except Exception:
        logger.exception("Failed to publish user event for %s", user_id)


async def listen_user_events(handler: Callable[[str, dict], Awaitable[None]]) -> None:
    """Subscribe to all user-events:* channels and dispatch to handler.

    Intended to be scheduled as a single asyncio task in the app lifespan.
    Any connection failure is logged and the task exits cleanly so it
    doesn't crash the app when Redis is unreachable (e.g. in local dev
    without Redis running).
    """
    try:
        client = aioredis.from_url(settings.redis_url)
        pubsub = client.pubsub()
        await pubsub.psubscribe(f"{USER_EVENT_CHANNEL_PREFIX}*")
    except Exception:
        logger.exception("Realtime event listener could not connect to Redis")
        return

    try:
        async for msg in pubsub.listen():
            if msg.get("type") != "pmessage":
                continue
            raw_channel = msg.get("channel")
            channel = raw_channel.decode() if isinstance(raw_channel, bytes) else raw_channel
            user_id = channel[len(USER_EVENT_CHANNEL_PREFIX):]
            try:
                data = json.loads(msg["data"])
            except Exception:
                logger.warning("Dropping malformed event on %s", channel)
                continue
            try:
                await handler(user_id, data)
            except Exception:
                logger.exception("User-event handler failed for %s", user_id)
    finally:
        try:
            await pubsub.punsubscribe()
            await pubsub.aclose()
            await client.aclose()
        except Exception:
            pass
