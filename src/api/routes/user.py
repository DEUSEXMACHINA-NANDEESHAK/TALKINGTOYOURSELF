"""
EchoAgent — User & Profile Endpoints
User profile lookups, voice model readiness status, and 'Record Again' flow.
"""

from datetime import datetime, timezone
import uuid
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from redis.asyncio import Redis

from src.api.dependencies import check_rate_limit, get_redis
from src.api.schemas import (
    SessionResponse,
    UserProfileResponse,
    VoiceProfileResponse,
)
from src.core.config import get_settings
from src.core.constants import (
    CHUNK_DURATION_SECONDS,
    MAX_SESSION_DURATION_SECONDS,
    REDIS_SESSION_PREFIX,
    REDIS_USER_PREFIX,
    SESSION_TTL_SECONDS,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/user", tags=["User"])


@router.get(
    "/{user_id}",
    response_model=UserProfileResponse,
    summary="Get user profile and voice model readiness status",
)
async def get_user_profile(
    user_id: uuid.UUID,
    redis: Redis = Depends(get_redis),
):
    """Retrieve user metadata and verify whether their personal voice model is ready to speak."""
    user_key = f"{REDIS_USER_PREFIX}{user_id}"
    user_data = await redis.hgetall(user_key)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    voice_profile = None
    if user_data.get("model_uri"):
        voice_profile = VoiceProfileResponse(
            profile_id=uuid.uuid4(),
            model_uri=user_data["model_uri"],
            model_version=int(user_data.get("model_version", 1)),
            quality_score=float(user_data["quality_score"]) if user_data.get("quality_score") else None,
            created_at=datetime.fromisoformat(user_data.get("model_created_at", datetime.now(timezone.utc).isoformat())),
        )

    is_ready = user_data.get("is_model_ready", "false").lower() == "true"

    return UserProfileResponse(
        user_id=user_id,
        display_name=user_data.get("display_name"),
        session_count=int(user_data.get("session_count", 1)),
        is_model_ready=is_ready,
        voice_profile=voice_profile,
        created_at=datetime.fromisoformat(user_data.get("created_at", datetime.now(timezone.utc).isoformat())),
    )


@router.post(
    "/{user_id}/record-again",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(check_rate_limit)],
    summary="Record again — issue a fresh session for retraining",
)
async def record_again(
    user_id: uuid.UUID,
    request: Request,
    redis: Redis = Depends(get_redis),
):
    """Initiates a new voice session linked to the existing user ID."""
    settings = get_settings()
    session_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    host = request.headers.get("host", f"{settings.api_host}:{settings.api_port}")
    is_https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    ws_proto = "wss" if is_https else "ws"
    http_proto = "https" if is_https else "http"

    ws_url = f"{ws_proto}://{host}/ws/converse/{session_id}"
    sse_url = f"{http_proto}://{host}/sse/status/{session_id}"

    # Create session in Redis with user_id attached
    session_data = {
        "session_id": str(session_id),
        "user_id": str(user_id),
        "status": "active",
        "chunk_count": "0",
        "duration_ms": "0",
        "created_at": now.isoformat(),
        "job_id": "",
        "model_id": "",
    }

    session_key = f"{REDIS_SESSION_PREFIX}{session_id}"
    user_key = f"{REDIS_USER_PREFIX}{user_id}"

    pipe = redis.pipeline(transaction=True)
    pipe.hset(session_key, mapping=session_data)
    pipe.expire(session_key, SESSION_TTL_SECONDS)
    pipe.hincrby(user_key, "session_count", 1)
    await pipe.execute()

    logger.info("record_again_session_created", user_id=str(user_id), session_id=str(session_id))

    return SessionResponse(
        session_id=session_id,
        user_id=user_id,
        status="active",
        ws_url=ws_url,
        sse_url=sse_url,
        max_duration_seconds=MAX_SESSION_DURATION_SECONDS,
        chunk_interval_seconds=int(CHUNK_DURATION_SECONDS),
        created_at=now,
    )

