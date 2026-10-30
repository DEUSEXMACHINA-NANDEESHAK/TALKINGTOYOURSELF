"""
EchoAgent — Session Management Endpoints
Handles creation, status polling, and metadata tracking for voice sessions.
"""

from datetime import datetime, timezone
import json
import uuid
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from redis.asyncio import Redis

from src.api.dependencies import check_rate_limit, get_redis
from src.api.schemas import (
    CreateSessionRequest,
    SessionDetailResponse,
    SessionResponse,
)
from src.core.config import get_settings
from src.core.constants import (
    CHUNK_DURATION_SECONDS,
    MAX_SESSION_DURATION_SECONDS,
    REDIS_SESSION_PREFIX,
    SESSION_TTL_SECONDS,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/session", tags=["Session"])


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(check_rate_limit)],
    summary="Create a new voice conversation session",
)
async def create_session(
    request: Request,
    payload: CreateSessionRequest | None = None,
    redis: Redis = Depends(get_redis),
):
    """Initializes a new voice session, reserves Redis state, and returns WebSocket/SSE coordinates."""
    settings = get_settings()
    session_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # Derive host/scheme for WebSocket and SSE URLs
    host = request.headers.get("host", f"{settings.api_host}:{settings.api_port}")
    is_https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    ws_proto = "wss" if is_https else "ws"
    http_proto = "https" if is_https else "http"

    ws_url = f"{ws_proto}://{host}/ws/converse/{session_id}"
    sse_url = f"{http_proto}://{host}/sse/status/{session_id}"

    session_data = {
        "session_id": str(session_id),
        "status": "active",
        "display_name": payload.display_name if payload else "",
        "chunk_count": "0",
        "duration_ms": "0",
        "created_at": now.isoformat(),
        "job_id": "",
        "model_id": "",
    }

    session_key = f"{REDIS_SESSION_PREFIX}{session_id}"
    pipe = redis.pipeline(transaction=True)
    pipe.hset(session_key, mapping=session_data)
    pipe.expire(session_key, SESSION_TTL_SECONDS)
    await pipe.execute()

    logger.info("session_created", session_id=str(session_id))

    return SessionResponse(
        session_id=session_id,
        status="active",
        ws_url=ws_url,
        sse_url=sse_url,
        max_duration_seconds=MAX_SESSION_DURATION_SECONDS,
        chunk_interval_seconds=int(CHUNK_DURATION_SECONDS),
        created_at=now,
    )


@router.get(
    "/{session_id}",
    response_model=SessionDetailResponse,
    summary="Get session details and processing status",
)
async def get_session(
    session_id: uuid.UUID,
    redis: Redis = Depends(get_redis),
):
    """Retrieve current state and telemetry for an active or completed session."""
    session_key = f"{REDIS_SESSION_PREFIX}{session_id}"
    data = await redis.hgetall(session_key)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found or expired.",
        )

    completed_at = None
    if data.get("completed_at"):
        completed_at = datetime.fromisoformat(data["completed_at"])

    return SessionDetailResponse(
        session_id=uuid.UUID(data["session_id"]),
        user_id=uuid.UUID(data["user_id"]) if data.get("user_id") else None,
        status=data.get("status", "active"),
        chunk_count=int(data.get("chunk_count", 0)),
        duration_ms=int(data.get("duration_ms", 0)),
        job_id=data.get("job_id") or None,
        model_id=data.get("model_id") or None,
        created_at=datetime.fromisoformat(data["created_at"]),
        completed_at=completed_at,
    )

