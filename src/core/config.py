"""
EchoAgent — Core Configuration
Environment-driven settings using Pydantic Settings.
All configuration is read from environment variables or .env file.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings — loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────
    app_name: str = "echoagent"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"

    # ── API Server ───────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # ── Redis ────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 20

    # ── RabbitMQ ─────────────────────────────────
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672//"

    # ── PostgreSQL ───────────────────────────────
    database_url: str = "postgresql+asyncpg://echo:secret@localhost:5432/echoagent"

    # ── MLflow ───────────────────────────────────
    mlflow_tracking_uri: str = "sqlite:///./data/mlflow.db"
    mlflow_default_artifact_root: str = "./data/mlflow-artifacts"

    # ── LLM Providers ───────────────────────────
    groq_api_key: str = ""
    huggingface_api_key: str = ""

    # ── Audio ────────────────────────────────────
    audio_storage_path: str = "./data/audio"
    max_session_duration_seconds: int = 120
    audio_chunk_interval_seconds: int = 2
    audio_sample_rate: int = 16000

    # ── Rate Limiting ────────────────────────────
    rate_limit_requests_per_minute: int = 100
    rate_limit_sessions_per_hour: int = 3

    @property
    def audio_storage_dir(self) -> Path:
        """Return audio storage as a Path object, creating it if needed."""
        path = Path(self.audio_storage_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton — loaded once per process."""
    return Settings()

