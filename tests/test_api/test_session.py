"""
EchoAgent — Session API & Rate Limiting Tests
"""

import uuid
import pytest
from src.utils.rate_limiter import SlidingWindowRateLimiter


@pytest.mark.asyncio
async def test_create_session_success(client):
    """POST /api/v1/session creates a new session in Redis and returns URLs."""
    response = await client.post("/api/v1/session", json={"display_name": "Test User"})
    assert response.status_code == 201
    data = response.json()

    assert "session_id" in data
    assert data["status"] == "active"
    assert "ws_url" in data
    assert "sse_url" in data
    assert data["max_duration_seconds"] == 120
    assert data["chunk_interval_seconds"] == 2

    # Verify session ID is valid UUID
    parsed_uuid = uuid.UUID(data["session_id"])
    assert str(parsed_uuid) == data["session_id"]


@pytest.mark.asyncio
async def test_get_session_details(client):
    """GET /api/v1/session/{id} returns saved session data."""
    # 1. Create session
    create_res = await client.post("/api/v1/session", json={"display_name": "Speaker 1"})
    assert create_res.status_code == 201
    session_id = create_res.json()["session_id"]

    # 2. Fetch session
    get_res = await client.get(f"/api/v1/session/{session_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["session_id"] == session_id
    assert data["status"] == "active"
    assert data["chunk_count"] == 0


@pytest.mark.asyncio
async def test_get_nonexistent_session_returns_404(client):
    """GET /api/v1/session/{id} with unknown ID returns 404."""
    random_id = uuid.uuid4()
    response = await client.get(f"/api/v1/session/{random_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_sliding_window_rate_limiter(fake_redis):
    """Rate limiter allows requests within limit and throttles excess."""
    limiter = SlidingWindowRateLimiter(fake_redis)
    test_key = "ratelimit:test:ip"

    # Allow 3 requests in a 10s window
    allowed_1, rem_1, _ = await limiter.is_allowed(test_key, max_requests=3, window_seconds=10)
    allowed_2, rem_2, _ = await limiter.is_allowed(test_key, max_requests=3, window_seconds=10)
    allowed_3, rem_3, _ = await limiter.is_allowed(test_key, max_requests=3, window_seconds=10)

    assert allowed_1 is True
    assert allowed_2 is True
    assert allowed_3 is True
    assert rem_3 == 0

    # 4th request must be denied
    allowed_4, rem_4, retry_after = await limiter.is_allowed(test_key, max_requests=3, window_seconds=10)
    assert allowed_4 is False
    assert rem_4 == 0
    assert retry_after > 0

