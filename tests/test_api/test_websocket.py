"""
EchoAgent — WebSocket Audio Streaming Tests
"""

import json
from pathlib import Path
import tempfile
import uuid
import pytest
from starlette.testclient import TestClient

from src.core.constants import MAX_CHUNK_SIZE_BYTES, REDIS_SESSION_PREFIX
from src.utils.audio_io import create_mock_wav_bytes


def test_websocket_rejects_unregistered_session(app):
    """Connecting to WebSocket with an unknown session ID should close with 1008."""
    client = TestClient(app)
    random_session_id = str(uuid.uuid4())

    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/converse/{random_session_id}") as websocket:
            websocket.receive_text()


def test_websocket_streaming_and_concatenation(app, fake_redis, tmp_path):
    """WebSocket accepts audio chunks, updates telemetry, and finishes session."""
    client = TestClient(app)

    # 1. Create a session via REST API
    res = client.post("/api/v1/session", json={"display_name": "Speaker Bob"})
    assert res.status_code == 201
    session_id = res.json()["session_id"]

    # 2. Connect over WebSocket
    with client.websocket_connect(f"/ws/converse/{session_id}") as ws:
        # Initial greeting message
        greeting = json.loads(ws.receive_text())
        assert greeting["type"] == "transcript"
        assert "EchoAgent" in greeting["text"]

        # Heartbeat timer message
        timer_msg = json.loads(ws.receive_text())
        assert timer_msg["type"] == "timer"
        assert "remaining" in timer_msg

        # 3. Stream 2 binary chunks of simulated audio
        chunk_1 = b"\x00\x00" * 8000  # 16000 bytes PCM (0.5 sec)
        chunk_2 = b"\x00\x00" * 8000  # 16000 bytes PCM (0.5 sec)
        ws.send_bytes(chunk_1)
        ws.send_bytes(chunk_2)

        # 4. End conversation
        ws.send_text(json.dumps({"type": "end"}))

        # 5. Receive session_end event
        # Skip any timer ticks that arrived before end
        while True:
            msg = json.loads(ws.receive_text())
            if msg["type"] == "session_end":
                assert msg["session_id"] == session_id
                assert msg["chunks"] == 2
                assert msg["duration_seconds"] >= 0.5
                break


def test_websocket_rejects_oversized_chunk(app):
    """Sending a chunk larger than MAX_CHUNK_SIZE_BYTES returns error message."""
    client = TestClient(app)
    res = client.post("/api/v1/session")
    session_id = res.json()["session_id"]

    with client.websocket_connect(f"/ws/converse/{session_id}") as ws:
        # Read greeting
        ws.receive_text()

        # Send chunk that exceeds limit
        oversized = b"\x00" * (MAX_CHUNK_SIZE_BYTES + 1024)
        ws.send_bytes(oversized)

        # Read until error message is received
        found_error = False
        for _ in range(5):
            msg = json.loads(ws.receive_text())
            if msg["type"] == "error":
                assert msg["code"] == "CHUNK_TOO_LARGE"
                found_error = True
                break

        assert found_error is True
        ws.send_text(json.dumps({"type": "end"}))
