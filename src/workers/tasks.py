"""
EchoAgent — Celery Background Tasks
Audio feature extraction, model training, MLflow registration, and progress dispatch.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import structlog
from celery import shared_task
import redis

from src.core.config import get_settings
from src.core.constants import (
    PROCESSING_STEPS,
    REDIS_PROGRESS_CHANNEL_PREFIX,
    REDIS_SESSION_PREFIX,
    TOTAL_PROCESSING_STEPS,
)
from src.core.exceptions import EchoAgentError

logger = structlog.get_logger(__name__)


def _publish_progress(
    redis_client: redis.Redis,
    session_id: str,
    step: int,
    status: str,
    label: str,
    progress_percent: float = 0.0,
    metadata: dict | None = None,
) -> None:
    """Helper to publish progress events to Redis pub/sub channel."""
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
        redis_client.publish(channel, json.dumps(payload))
    except Exception as exc:
        logger.warning("progress_publish_failed", channel=channel, error=str(exc))


@shared_task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    name="src.workers.tasks.process_voice_recording",
)
def process_voice_recording(
    self,
    session_id: str,
    audio_path: str,
    user_id: str | None = None,
) -> dict:
    """Asynchronous background pipeline for processing user audio.

    Steps:
      1. Audio cleaning and silence trimming
      2. Mel-Spectrogram & feature extraction
      3. Speaker embedding generation (d-vector)
      4. Voice model training
      5. Validation & registration in MLflow
    """
    settings = get_settings()
    sync_redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    session_key = f"{REDIS_SESSION_PREFIX}{session_id}"

    logger.info(
        "voice_processing_started",
        task_id=self.request.id,
        session_id=session_id,
        audio_path=audio_path,
        retry=self.request.retries,
    )

    try:
        # ── Step 1: Cleaning & Trimming ──────────────
        _publish_progress(
            sync_redis,
            session_id,
            step=1,
            status="started",
            label=PROCESSING_STEPS[0]["label"],
            progress_percent=10.0,
        )
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        from src.ml.audio_preprocessor import clean_and_normalize_audio
        cleaned_audio_path, cleaned_duration = clean_and_normalize_audio(audio_file)

        _publish_progress(
            sync_redis,
            session_id,
            step=1,
            status="completed",
            label=PROCESSING_STEPS[0]["label"],
            progress_percent=20.0,
            metadata={"cleaned_duration": round(cleaned_duration, 2)},
        )

        # ── Step 2: Feature Extraction ───────────────
        _publish_progress(
            sync_redis,
            session_id,
            step=2,
            status="started",
            label=PROCESSING_STEPS[1]["label"],
            progress_percent=30.0,
        )
        from src.ml.feature_extractor import extract_all_features
        features = extract_all_features(cleaned_audio_path)

        _publish_progress(
            sync_redis,
            session_id,
            step=2,
            status="completed",
            label=PROCESSING_STEPS[1]["label"],
            progress_percent=40.0,
            metadata={"frames": features["frame_count"]},
        )

        # ── Step 3: Speaker Embedding ────────────────
        _publish_progress(
            sync_redis,
            session_id,
            step=3,
            status="started",
            label=PROCESSING_STEPS[2]["label"],
            progress_percent=50.0,
        )
        # Compute mean feature vector as speaker representation
        speaker_embedding = features["mfccs"].mean(axis=0)
        _publish_progress(
            sync_redis,
            session_id,
            step=3,
            status="completed",
            label=PROCESSING_STEPS[2]["label"],
            progress_percent=60.0,
        )

        # ── Step 4: Model Training (Pitch Predictor) ──
        _publish_progress(
            sync_redis,
            session_id,
            step=4,
            status="started",
            label=PROCESSING_STEPS[3]["label"],
            progress_percent=70.0,
        )
        from src.ml.pitch_predictor import PitchPredictorModel
        model = PitchPredictorModel(alpha=1.0)
        metrics = model.train(features["mfccs"], features["f0"])
        model_artifact_path = model.save(cleaned_audio_path.parent / "pitch_model.joblib")

        _publish_progress(
            sync_redis,
            session_id,
            step=4,
            status="completed",
            label=PROCESSING_STEPS[3]["label"],
            progress_percent=80.0,
            metadata=metrics,
        )

        # ── Step 5: Validation & Registration ────────
        _publish_progress(
            sync_redis,
            session_id,
            step=5,
            status="started",
            label=PROCESSING_STEPS[4]["label"],
            progress_percent=90.0,
        )
        from src.ml.registry import ModelRegistryService
        registry = ModelRegistryService()
        registry.validate_pitch_predictor(model, test_features=features["mfccs"][:5])

        model_id = registry.log_and_register_run(
            experiment_name="echoagent-voice-pipeline",
            run_name=f"session-{session_id}",
            params={"alpha": 1.0, "frames": features["frame_count"]},
            metrics=metrics,
            artifacts=[model_artifact_path],
            tags={"session_id": session_id, "user_id": user_id or "anonymous"},
        )

        _publish_progress(
            sync_redis,
            session_id,
            step=5,
            status="completed",
            label=PROCESSING_STEPS[4]["label"],
            progress_percent=100.0,
            metadata={"model_id": model_id},
        )

        # Update Redis state to complete
        sync_redis.hset(
            session_key,
            mapping={
                "status": "complete",
                "model_id": model_id,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.info("voice_processing_success", session_id=session_id, model_id=model_id)

        return {
            "status": "complete",
            "session_id": session_id,
            "model_id": model_id,
            "user_id": user_id,
        }

    except Exception as exc:
        logger.error(
            "voice_processing_error",
            task_id=self.request.id,
            session_id=session_id,
            error=str(exc),
            retry=self.request.retries,
        )
        sync_redis.hset(session_key, "status", "failed")
        _publish_progress(
            sync_redis,
            session_id,
            step=1,
            status="failed",
            label="Processing failed",
            metadata={"error": str(exc)},
        )
        raise exc
