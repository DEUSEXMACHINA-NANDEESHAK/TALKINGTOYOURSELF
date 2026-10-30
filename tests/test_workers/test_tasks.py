"""
EchoAgent — Celery Worker Task Tests
"""

import uuid
import pytest
from celery.exceptions import Retry

from src.utils.audio_io import create_mock_wav_bytes
from src.workers.celery_app import celery_app
from src.workers.tasks import process_voice_recording


@pytest.fixture(autouse=True)
def configure_celery_eager(tmp_path, monkeypatch):
    """Run Celery tasks synchronously in tests and use local SQLite MLflow."""
    monkeypatch.setenv("MLFLOW_TRACKING_URI", f"sqlite:///{tmp_path}/mlflow.db")
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
    )


def test_process_voice_recording_success(tmp_path, fake_sync_redis, monkeypatch):
    """Task executes through the pipeline and marks session complete in Redis."""
    monkeypatch.setattr("redis.Redis.from_url", lambda *args, **kwargs: fake_sync_redis)

    session_id = str(uuid.uuid4())
    fake_audio = tmp_path / "full_recording.wav"
    fake_audio.write_bytes(create_mock_wav_bytes(duration_seconds=1.0))

    # Initialize session in fake sync redis
    fake_sync_redis.hset(f"session:{session_id}", "status", "processing")

    # Run task
    result = process_voice_recording.apply(args=[session_id, str(fake_audio)]).get()

    assert result["status"] == "complete"
    assert result["session_id"] == session_id
    assert "runs:/" in result["model_id"] or "models:/" in result["model_id"]

    # Verify Redis status updated synchronously
    session_data = fake_sync_redis.hgetall(f"session:{session_id}")
    assert session_data["status"] == "complete"
    assert "runs:/" in session_data["model_id"] or "models:/" in session_data["model_id"]


def test_process_voice_recording_missing_file_triggers_retry(fake_sync_redis, monkeypatch):
    """Task catches missing file and initiates retry backoff."""
    monkeypatch.setattr("redis.Redis.from_url", lambda *args, **kwargs: fake_sync_redis)

    session_id = str(uuid.uuid4())
    non_existent = "/tmp/does_not_exist_12345.wav"

    with pytest.raises((FileNotFoundError, Retry)):
        process_voice_recording.apply(args=[session_id, non_existent]).get()

    session_data = fake_sync_redis.hgetall(f"session:{session_id}")
    assert session_data.get("status") == "failed"
