"""
EchoAgent — Real-Time Conversational Voice WebSocket
Manages the bidirectional 120-second streaming session.
"""

from datetime import datetime, timezone
import json
import uuid
import structlog
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from redis.asyncio import Redis

from src.api.dependencies import get_redis
from src.core.config import get_settings
from src.core.constants import (
    MAX_CHUNK_SIZE_BYTES,
    MAX_SESSION_DURATION_SECONDS,
    REDIS_SESSION_PREFIX,
    WS_TYPE_AUDIO,
    WS_TYPE_ERROR,
    WS_TYPE_SESSION_END,
    WS_TYPE_TIMER,
    WS_TYPE_TRANSCRIPT,
)
from src.utils.audio_io import (
    concatenate_chunks_to_wav,
    get_session_audio_dir,
    save_audio_chunk,
)

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/converse/{session_id}")
async def converse_websocket(
    websocket: WebSocket,
    session_id: uuid.UUID,
    redis: Redis = Depends(get_redis),
):
    """Real-time voice conversation WebSocket handler.

    Receives binary audio chunks, stores them to disk, updates Redis telemetry,
    and returns conversational responses and timer updates.
    """
    settings = get_settings()
    session_key = f"{REDIS_SESSION_PREFIX}{session_id}"

    # Verify session exists and is active in Redis
    session_data = await redis.hgetall(session_key)
    if not session_data or session_data.get("status") != "active":
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid or expired session ID",
        )
        return

    await websocket.accept()
    session_dir = get_session_audio_dir(settings.audio_storage_dir, str(session_id))
    logger.info("websocket_connected", session_id=str(session_id))

    chunk_sequence = 0
    start_time = datetime.now(timezone.utc)

    # Initial greeting from AI voice bot
    await websocket.send_text(
        json.dumps({
            "type": WS_TYPE_TRANSCRIPT,
            "text": "Hey there! I am EchoAgent. Let us talk for a couple of minutes to get to know each other. How has your day been so far?",
        })
    )

    try:
        while True:
            # Check elapsed time
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            remaining = max(0, int(MAX_SESSION_DURATION_SECONDS - elapsed))

            # Send heartbeat timer update
            await websocket.send_text(
                json.dumps({
                    "type": WS_TYPE_TIMER,
                    "remaining": remaining,
                    "elapsed": int(elapsed),
                })
            )

            # Receive next message (can be binary audio chunk or JSON text control)
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            if "bytes" in message and message["bytes"]:
                chunk_bytes = message["bytes"]
                if len(chunk_bytes) > MAX_CHUNK_SIZE_BYTES:
                    await websocket.send_text(
                        json.dumps({
                            "type": WS_TYPE_ERROR,
                            "code": "CHUNK_TOO_LARGE",
                            "message": f"Chunk exceeded maximum allowed limit ({len(chunk_bytes)} > {MAX_CHUNK_SIZE_BYTES})",
                        })
                    )
                    continue

                chunk_sequence += 1
                save_audio_chunk(session_dir, chunk_sequence, chunk_bytes)

                # Update Redis session telemetry
                await redis.hset(
                    session_key,
                    mapping={
                        "chunk_count": str(chunk_sequence),
                        "duration_ms": str(int(elapsed * 1000)),
                    },
                )

            elif "text" in message and message["text"]:
                try:
                    payload = json.loads(message["text"])
                    if payload.get("type") in ("end", "session_end"):
                        break
                except json.JSONDecodeError:
                    pass

            if remaining <= 0:
                break

    except WebSocketDisconnect:
        logger.info("websocket_disconnected_by_client", session_id=str(session_id))

    finally:
        # Wrap up session if at least one chunk was received
        if chunk_sequence > 0:
            try:
                wav_path, total_bytes, duration_s = concatenate_chunks_to_wav(
                    session_dir=session_dir,
                    sample_rate=settings.audio_sample_rate,
                )

                # Enqueue background processing job via Celery & RabbitMQ
                job_id = ""
                try:
                    from src.workers.tasks import process_voice_recording
                    task = process_voice_recording.delay(str(session_id), str(wav_path))
                    job_id = task.id
                except Exception as q_exc:
                    logger.warning("queue_dispatch_warning", session_id=str(session_id), error=str(q_exc))

                await redis.hset(
                    session_key,
                    mapping={
                        "status": "processing",
                        "audio_path": str(wav_path),
                        "chunk_count": str(chunk_sequence),
                        "duration_ms": str(int(duration_s * 1000)),
                        "job_id": job_id,
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
                # Send session end event with SSE status URL
                try:
                    await websocket.send_text(
                        json.dumps({
                            "type": WS_TYPE_SESSION_END,
                            "session_id": str(session_id),
                            "duration_seconds": round(duration_s, 2),
                            "chunks": chunk_sequence,
                            "sse_url": f"/sse/status/{session_id}",
                        })
                    )
                except Exception:
                    pass  # Client might have closed the socket already

            except Exception as exc:
                logger.error("session_wrap_up_failed", session_id=str(session_id), error=str(exc))
                await redis.hset(session_key, "status", "failed")
