"""
EchoAgent — Server-Sent Events (SSE) Endpoint
Streams real-time background processing telemetry to client browsers.
"""

import uuid
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis

from src.api.dependencies import get_redis
from src.notifications.subscriber import stream_progress_events

router = APIRouter(prefix="/sse", tags=["Notifications"])


@router.get(
    "/status/{session_id}",
    summary="Server-Sent Events stream for background processing status",
    responses={
        status.HTTP_200_OK: {
            "description": "Continuous event stream (text/event-stream)",
            "content": {"text/event-stream": {}},
        }
    },
)
async def get_progress_sse_stream(
    session_id: uuid.UUID,
    redis: Redis = Depends(get_redis),
):
    """Establishes a persistent SSE connection to report live progress.

    Client receives:
      - 'connected': Handshake confirmed
      - 'progress': Step updates (1 to 5) with percentages and labels
      - 'heartbeat': Sent every 15s to keep proxy connections alive
      - 'complete': Training finished, voice profile ready
      - 'error': Processing failed
    """
    generator = stream_progress_events(redis_client=redis, session_id=str(session_id))

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disables proxy buffering in Nginx/Caddy
        },
    )

