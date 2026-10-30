"""
EchoAgent — Celery Application & Broker Configuration
Robust enterprise task queue setup with RabbitMQ exchanges, DLQ, and retry routing.
"""

from celery import Celery
from kombu import Exchange, Queue

from src.core.config import get_settings
from src.core.constants import (
    DEAD_LETTER_QUEUE,
    MESSAGE_TTL_MS,
    QUEUE_MAX_LENGTH,
    VOICE_CLONE_QUEUE,
    VOICE_PROCESS_QUEUE,
)

settings = get_settings()

celery_app = Celery(
    "echoagent",
    broker=settings.rabbitmq_url,
    backend=settings.redis_url,
    include=["src.workers.tasks"],
)

# ── Exchanges ────────────────────────────────────
default_exchange = Exchange("echoagent.direct", type="direct")
dlx_exchange = Exchange("echoagent.dlx", type="fanout")

# ── Queue Definitions & DLQ Bindings ─────────────
celery_app.conf.task_queues = (
    # Main voice processing queue
    Queue(
        VOICE_PROCESS_QUEUE,
        exchange=default_exchange,
        routing_key="voice.process",
        queue_arguments={
            "x-message-ttl": MESSAGE_TTL_MS,
            "x-max-length": QUEUE_MAX_LENGTH,
            "x-dead-letter-exchange": "echoagent.dlx",
        },
    ),
    # Cloned voice generation queue
    Queue(
        VOICE_CLONE_QUEUE,
        exchange=default_exchange,
        routing_key="voice.clone",
        queue_arguments={
            "x-message-ttl": MESSAGE_TTL_MS // 2,
            "x-max-length": QUEUE_MAX_LENGTH,
            "x-dead-letter-exchange": "echoagent.dlx",
        },
    ),
    # Dead-Letter Queue (DLQ) for permanently failed tasks
    Queue(
        DEAD_LETTER_QUEUE,
        exchange=dlx_exchange,
        queue_arguments={
            "x-max-length": QUEUE_MAX_LENGTH,
        },
    ),
)

# ── Task Routing Map ─────────────────────────────
celery_app.conf.task_routes = {
    "src.workers.tasks.process_voice_recording": {
        "queue": VOICE_PROCESS_QUEUE,
        "routing_key": "voice.process",
    },
    "src.workers.tasks.clone_voice_session": {
        "queue": VOICE_CLONE_QUEUE,
        "routing_key": "voice.clone",
    },
}

# ── Worker Tuning & Resiliency ───────────────────
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,               # Acknowledge task only after execution finishes
    task_reject_on_worker_lost=True,   # Requeue task if worker process is abruptly killed
    worker_prefetch_multiplier=1,      # Single task per worker process (CPU-intensive ML)
    task_time_limit=600,               # Hard kill after 10 minutes
    task_soft_time_limit=540,          # Soft warning exception at 9 minutes
    result_expires=3600,               # Celery results expire in 1 hour
)

