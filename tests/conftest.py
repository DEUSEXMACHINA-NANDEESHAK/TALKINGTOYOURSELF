"""
EchoAgent — Test Configuration and Fixtures
"""

import fakeredis
import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient

from src.api.dependencies import get_redis
from src.api.main import create_app
from src.core.config import Settings, get_settings


def get_test_settings() -> Settings:
    return Settings(
        app_env="development",
        debug=True,
        audio_storage_path="./data/test_audio",
        redis_url="redis://localhost:6379/15",
        rabbitmq_url="amqp://guest:guest@localhost:5672//",
        database_url="postgresql+asyncpg://echo:secret@localhost:5432/echoagent_test",
        mlflow_tracking_uri="sqlite:///./data/test_mlflow.db",
    )


@pytest.fixture
def fake_redis_server():
    """Shared in-memory fake redis state."""
    return fakeredis.FakeServer()


@pytest.fixture
def fake_async_redis(fake_redis_server):
    """Async in-memory Redis for FastAPI."""
    return fakeredis.aioredis.FakeRedis(server=fake_redis_server, decode_responses=True)


@pytest.fixture
def fake_sync_redis(fake_redis_server):
    """Synchronous in-memory Redis for Celery workers."""
    return fakeredis.FakeRedis(server=fake_redis_server, decode_responses=True)


# Backwards compatibility alias
@pytest.fixture
def fake_redis(fake_async_redis):
    return fake_async_redis


@pytest.fixture
def app(fake_async_redis):
    """Create a fresh app instance for testing with mocked dependencies."""
    test_app = create_app()
    test_app.dependency_overrides[get_settings] = get_test_settings

    async def override_get_redis():
        yield fake_async_redis

    test_app.dependency_overrides[get_redis] = override_get_redis
    return test_app


@pytest.fixture
async def client(app):
    """Async HTTP client for testing API endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
