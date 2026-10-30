"""
EchoAgent — Cloned Voice WebSocket Tests ("Speak to Yourself")
"""

import json
import uuid
import pytest
from starlette.testclient import TestClient


def test_clone_websocket_rejects_unready_user(app):
    """Connecting to /ws/clone before voice model training is complete closes with 1008."""
    client = TestClient(app)
    unready_user_id = str(uuid.uuid4())

    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/clone/{unready_user_id}") as ws:
            ws.receive_text()


@pytest.mark.asyncio
async def test_clone_websocket_full_conversation_flow(app, fake_async_redis):
    """Connecting with ready voice profile initiates conversation in cloned voice."""
    client = TestClient(app)
    user_id = uuid.uuid4()

    # Seed user in fake Redis with is_model_ready = true
    await fake_async_redis.hset(
        f"user:{user_id}",
        mapping={
            "display_name": "Charlie",
            "is_model_ready": "true",
            "model_uri": "models:/voice-clone-charlie/1",
        },
    )

    with client.websocket_connect(f"/ws/clone/{user_id}") as ws:
        # 1. Receive greeting transcript
        greeting_msg = json.loads(ws.receive_text())
        assert greeting_msg["type"] == "transcript"
        assert greeting_msg["speaker"] == "your_cloned_voice"
        assert "Charlie" in greeting_msg["text"]

        # 2. Receive cloned greeting audio bytes
        audio_bytes = ws.receive_bytes()
        assert len(audio_bytes) > 0
        assert audio_bytes.startswith(b"RIFF")  # Valid WAV header

        # 3. User responds to the bot
        ws.send_text(json.dumps({"text": "It sounds surreal to hear myself!"}))

        # 4. Cloned bot replies with synthesized speech
        reply_msg = json.loads(ws.receive_text())
        assert reply_msg["type"] == "transcript"
        assert reply_msg["speaker"] == "your_cloned_voice"

        reply_audio = ws.receive_bytes()
        assert len(reply_audio) > 0
        assert reply_audio.startswith(b"RIFF")

        # 5. End clone session
        ws.send_text(json.dumps({"type": "end"}))
