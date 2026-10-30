"""
EchoAgent — Notification Publisher
Dispatches real-time event updates to Redis Pub/Sub channels.
"""

from datetime import datetime, timezone
import json
from typing import Any
import redis.asyncio as aioredis
import structlog

from src.core.constants import REDIS_PROGRESS_CHANNEL_PREFIX, TOTAL_PROCESSING_STEPS

logger = structlog.get_logger(__name__)


async def publish_step_event(
    redis_client: aioredis.Redis,
    session_id: str,
    step: int,
    status: str,
    label: str,
    progress_percent: float = 0.0,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Publish an asynchronous progress update to the session channel."""
    channel = f"{REDIS_PROGRESS_CHANNEL_PREFIX}{session_id}"
    payload = {
        "step": step,
        "total_steps": TOTAL_PROCESSING_STEPS,
        "label": label,
        "status": status,
        "progress_percent": progress_percent,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    }
    try:
        await redis_client.publish(channel, json.dumps(payload))
        logger.debug("sse_event_published", channel=channel, step=step, status=status)
    except Exception as exc:
        logger.warning("sse_publish_failed", channel=channel, error=str(exc))

