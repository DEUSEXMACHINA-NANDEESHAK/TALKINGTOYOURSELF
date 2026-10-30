"""
EchoAgent — Notification Subscriber
Async generator that subscribes to Redis channels and yields Server-Sent Events (SSE).
"""

import asyncio
from datetime import datetime, timezone
import json
from typing import AsyncGenerator
import redis.asyncio as aioredis
import structlog

from src.core.constants import REDIS_PROGRESS_CHANNEL_PREFIX

logger = structlog.get_logger(__name__)


async def stream_progress_events(
    redis_client: aioredis.Redis,
    session_id: str,
    heartbeat_interval_seconds: int = 15,
) -> AsyncGenerator[str, None]:
    """Subscribes to session Redis channel and yields Server-Sent Events with heartbeats."""
    channel_name = f"{REDIS_PROGRESS_CHANNEL_PREFIX}{session_id}"
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel_name)

    logger.info("sse_client_subscribed", channel=channel_name)

    try:
        # Initial greeting event
        init_event = {
            "type": "connected",
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        yield f"event: connected\ndata: {json.dumps(init_event)}\n\n"

        while True:
            try:
                # Wait for message or heartbeat timeout
                msg = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                    timeout=heartbeat_interval_seconds,
                )

                if msg and msg.get("type") == "message":
                    raw_data = msg["data"]
                    # Forward event directly to SSE client
                    yield f"event: progress\ndata: {raw_data}\n\n"

                    # Check if event marks completion or permanent failure to close stream
                    try:
                        parsed = json.loads(raw_data)
                        if parsed.get("step") == 5 and parsed.get("status") == "completed":
                            yield f"event: complete\ndata: {raw_data}\n\n"
                            break
                        if parsed.get("status") == "failed":
                            yield f"event: error\ndata: {raw_data}\n\n"
                            break
                    except Exception:
                        pass
                else:
                    await asyncio.sleep(0.1)

            except asyncio.TimeoutError:
                # Emit keep-alive heartbeat comment/event
                heartbeat = {
                    "type": "heartbeat",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                yield f"event: heartbeat\ndata: {json.dumps(heartbeat)}\n\n"

    finally:
        await pubsub.unsubscribe(channel_name)
        await pubsub.aclose()
        logger.info("sse_client_unsubscribed", channel=channel_name)
