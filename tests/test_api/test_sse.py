"""
EchoAgent — Server-Sent Events (SSE) Tests
"""

import asyncio
import json
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from src.notifications.publisher import publish_step_event
from src.notifications.subscriber import stream_progress_events


@pytest.mark.asyncio
async def test_stream_progress_events_generator(fake_async_redis):
    """Direct generator test: yields connected handshake and receives published Redis events."""
    session_id = str(uuid.uuid4())
    generator = stream_progress_events(fake_async_redis, session_id=session_id)

    # 1. First yielded chunk is the connected handshake event
    first_event = await anext(generator)
    assert "event: connected" in first_event
    assert session_id in first_event

    # 2. Publish a step progress event in the background
    async def publish_later():
        await asyncio.sleep(0.05)
        await publish_step_event(
            redis_client=fake_async_redis,
            session_id=session_id,
            step=1,
            status="completed",
            label="Noise cleaned",
            progress_percent=20.0,
        )

    task = asyncio.create_task(publish_later())

    # 3. Next yielded event should be the published progress event
    progress_event = await anext(generator)
    assert "event: progress" in progress_event
    assert "Noise cleaned" in progress_event
    assert "20.0" in progress_event

    # Clean up generator
    await generator.aclose()
    await task


@pytest.mark.asyncio
async def test_stream_completion_event_closes_stream(fake_async_redis):
    """Publishing step 5 completed event emits complete event and terminates generator."""
    session_id = str(uuid.uuid4())
    generator = stream_progress_events(fake_async_redis, session_id=session_id)

    # Consume handshake
    await anext(generator)

    # Publish final step 5 completed
    await publish_step_event(
        redis_client=fake_async_redis,
        session_id=session_id,
        step=5,
        status="completed",
        label="Model registered",
        progress_percent=100.0,
    )

    # Yields progress event first
    ev1 = await anext(generator)
    assert "event: progress" in ev1

    # Yields complete event and finishes
    ev2 = await anext(generator)
    assert "event: complete" in ev2

    # Verify generator is exhausted (StopAsyncIteration)
    with pytest.raises(StopAsyncIteration):
        await anext(generator)

    await generator.aclose()
