"""
EchoAgent — User Profile and Record-Again Flow Tests
"""

from datetime import datetime, timezone
import uuid
import pytest


@pytest.mark.asyncio
async def test_get_user_profile_not_found(client):
    """Querying unknown user ID returns 404."""
    unknown_id = uuid.uuid4()
    response = await client.get(f"/api/v1/user/{unknown_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_user_profile_success(client, fake_async_redis):
    """Querying existing user returns profile, session count, and model readiness."""
    user_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # Seed user in fake Redis
    await fake_async_redis.hset(
        f"user:{user_id}",
        mapping={
            "display_name": "Alice Developer",
            "session_count": "2",
            "is_model_ready": "true",
            "model_uri": "models:/voice-clone-alice/1",
            "model_version": "1",
            "quality_score": "0.92",
            "created_at": now.isoformat(),
        },
    )

    response = await client.get(f"/api/v1/user/{user_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["user_id"] == str(user_id)
    assert data["display_name"] == "Alice Developer"
    assert data["session_count"] == 2
    assert data["is_model_ready"] is True
    assert data["voice_profile"]["model_uri"] == "models:/voice-clone-alice/1"
    assert data["voice_profile"]["quality_score"] == 0.92


@pytest.mark.asyncio
async def test_record_again_endpoint(client, fake_async_redis):
    """POST /api/v1/user/{user_id}/record-again creates fresh session attached to user."""
    user_id = uuid.uuid4()
    # Seed initial user
    await fake_async_redis.hset(f"user:{user_id}", "session_count", "1")

    response = await client.post(f"/api/v1/user/{user_id}/record-again")
    assert response.status_code == 201
    data = response.json()

    assert data["user_id"] == str(user_id)
    assert data["status"] == "active"
    assert "ws_url" in data
    assert "sse_url" in data

    # Verify session in Redis has user_id
    session_id = data["session_id"]
    session_data = await fake_async_redis.hgetall(f"session:{session_id}")
    assert session_data["user_id"] == str(user_id)

    # Verify session count incremented
    count = await fake_async_redis.hget(f"user:{user_id}", "session_count")
    assert count == "2"

