"""
EchoAgent — API Schemas
Pydantic v2 data models for request and response validation.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ── Health & System ──────────────────────────────
class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"] = "healthy"
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=utc_now)


class ReadinessResponse(BaseModel):
    status: Literal["ok", "degraded", "unavailable"]
    redis: bool
    rabbitmq: bool
    postgres: bool
    timestamp: datetime = Field(default_factory=utc_now)


# ── Session Schemas ──────────────────────────────
class CreateSessionRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)


class SessionResponse(BaseModel):
    session_id: UUID
    user_id: UUID | None = None
    status: Literal["active", "processing", "complete", "failed"] = "active"
    ws_url: str
    sse_url: str
    max_duration_seconds: int = 120
    chunk_interval_seconds: int = 2
    created_at: datetime = Field(default_factory=utc_now)


class SessionDetailResponse(BaseModel):
    session_id: UUID
    user_id: UUID | None = None
    status: Literal["active", "processing", "complete", "failed"]
    chunk_count: int = 0
    duration_ms: int = 0
    job_id: str | None = None
    model_id: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


# ── User & Voice Profile ─────────────────────────
class VoiceProfileResponse(BaseModel):
    profile_id: UUID
    model_uri: str
    model_version: int = 1
    quality_score: float | None = None
    created_at: datetime


class UserProfileResponse(BaseModel):
    user_id: UUID
    display_name: str | None = None
    session_count: int = 0
    is_model_ready: bool = False
    voice_profile: VoiceProfileResponse | None = None
    created_at: datetime


# ── Audio & WebSocket Events ─────────────────────
class WebSocketControlMessage(BaseModel):
    type: Literal["audio", "transcript", "timer", "session_end", "error", "slow_down"]
    data: str | None = None  # Base64 encoded audio or text payload
    text: str | None = None
    remaining: int | None = None
    session_id: str | None = None
    code: str | None = None
    message: str | None = None


# ── Server-Sent Events (SSE) ─────────────────────
class ProgressEventPayload(BaseModel):
    step: int
    total_steps: int = 5
    label: str
    progress_percent: float = 0.0
    status: Literal["started", "in_progress", "completed", "failed"]
    metadata: dict[str, Any] = Field(default_factory=dict)
