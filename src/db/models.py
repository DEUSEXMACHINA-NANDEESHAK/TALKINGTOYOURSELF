"""
EchoAgent — SQLAlchemy ORM Models
PostgreSQL tables for users, voice sessions, profiles, training runs, and notifications.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    BIGINT,
    BOOLEAN,
    FLOAT,
    INTEGER,
    TEXT,
    VARCHAR,
    Column,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """User profile registered with an IP hash."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name = Column(VARCHAR(255), nullable=True)
    ip_hash = Column(VARCHAR(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    session_count = Column(INTEGER, default=0, nullable=False)
    is_active = Column(BOOLEAN, default=True, nullable=False)

    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    voice_profiles = relationship("VoiceProfile", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    """Voice recording and conversation sessions."""

    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    status = Column(VARCHAR(20), default="active", nullable=False, index=True)
    audio_path = Column(TEXT, nullable=True)
    duration_ms = Column(INTEGER, default=0, nullable=False)
    chunk_count = Column(INTEGER, default=0, nullable=False)
    sample_rate = Column(INTEGER, default=16000, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column("metadata", JSONB, default=dict)

    # Relationships
    user = relationship("User", back_populates="sessions")
    voice_profile = relationship("VoiceProfile", back_populates="session", uselist=False)
    training_runs = relationship("TrainingRun", back_populates="session")


class VoiceProfile(Base):
    """Trained voice models associated with users."""

    __tablename__ = "voice_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    model_uri = Column(TEXT, nullable=False)
    model_version = Column(INTEGER, default=1, nullable=False)
    quality_score = Column(FLOAT, nullable=True)
    is_active = Column(BOOLEAN, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    metadata_json = Column("metadata", JSONB, default=dict)

    # Relationships
    user = relationship("User", back_populates="voice_profiles")
    session = relationship("Session", back_populates="voice_profile")


class TrainingRun(Base):
    """Audit log of ML training jobs and validation metrics."""

    __tablename__ = "training_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    mlflow_run_id = Column(VARCHAR(64), nullable=True)
    status = Column(VARCHAR(20), default="pending", nullable=False, index=True)
    model_type = Column(VARCHAR(50), default="pitch_predictor", nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(INTEGER, nullable=True)
    metrics = Column(JSONB, default=dict)
    error_message = Column(TEXT, nullable=True)
    retry_count = Column(INTEGER, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    session = relationship("Session", back_populates="training_runs")


class Notification(Base):
    """Persistent audit log of progress events dispatched during training."""

    __tablename__ = "notifications"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False, index=True)
    event_type = Column(VARCHAR(50), nullable=False)
    step_number = Column(INTEGER, nullable=True)
    step_label = Column(VARCHAR(100), nullable=True)
    payload = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

