"""
EchoAgent — Cloned Voice WebSocket ("Speak to Yourself")
Session 2: An interactive conversation where the AI responds in the user's own cloned voice.
"""

import base64
import json
import uuid
import numpy as np
import structlog
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from redis.asyncio import Redis

from src.agent.conversation_agent import ConversationAgent
from src.api.dependencies import get_redis
from src.core.constants import REDIS_USER_PREFIX, WS_TYPE_AUDIO, WS_TYPE_TRANSCRIPT
from src.ml.tts_engine import SyntheticTTSEngine

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/clone/{user_id}")
async def clone_websocket(
    websocket: WebSocket,
    user_id: uuid.UUID,
    redis: Redis = Depends(get_redis),
):
    """Real-time voice conversation where the AI speaks using the user's cloned voice profile."""
    user_key = f"{REDIS_USER_PREFIX}{user_id}"
    user_data = await redis.hgetall(user_key)

    # 1. Verify user exists and voice model is marked ready
    if not user_data or user_data.get("is_model_ready", "false").lower() != "true":
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Voice model is not ready yet. Complete Session 1 first.",
        )
        return

    await websocket.accept()
    logger.info("clone_session_connected", user_id=str(user_id))

    display_name = user_data.get("display_name")
    model_uri = user_data.get("model_uri", "models:/voice-clone/1")

    # 2. Initialize TTS engine with user's cloned voice profile
    tts = SyntheticTTSEngine()
    tts.load_voice_model(model_uri)

    # Synthetic speaker embedding simulation from user ID
    rng = np.random.default_rng(seed=abs(hash(str(user_id))) % (2**32))
    user_embedding = rng.normal(0, 1, 256).astype(np.float32)
    tts.speaker_embedding = user_embedding

    agent = ConversationAgent()

    # 3. Cloned voice speaks initial greeting
    greeting_text = agent.get_cloned_session_greeting(display_name)
    audio_bytes = tts.synthesize(greeting_text, speaker_embedding=user_embedding)

    await websocket.send_text(
        json.dumps({
            "type": WS_TYPE_TRANSCRIPT,
            "text": greeting_text,
            "speaker": "your_cloned_voice",
        })
    )
    # Stream binary audio frame (user hears their own voice!)
    await websocket.send_bytes(audio_bytes)

    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            user_transcript = None
            if "text" in message and message["text"]:
                try:
                    payload = json.loads(message["text"])
                    if payload.get("type") in ("end", "session_end"):
                        break
                    user_transcript = payload.get("text")
                except json.JSONDecodeError:
                    pass

            # Generate reply and synthesize with cloned voice
            response_text = agent.generate_response(user_transcript)
            cloned_audio_bytes = tts.synthesize(response_text, speaker_embedding=user_embedding)

            await websocket.send_text(
                json.dumps({
                    "type": WS_TYPE_TRANSCRIPT,
                    "text": response_text,
                    "speaker": "your_cloned_voice",
                })
            )
            await websocket.send_bytes(cloned_audio_bytes)

    except WebSocketDisconnect:
        logger.info("clone_session_disconnected", user_id=str(user_id))
    finally:
        logger.info("clone_session_closed", user_id=str(user_id))

