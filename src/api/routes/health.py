"""
EchoAgent — Health & Readiness Endpoints
Used by Docker healthchecks, Kubernetes liveness/readiness probes, and monitoring.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src.api.schemas import HealthResponse, ReadinessResponse
from src.core.config import get_settings

router = APIRouter(tags=["Health"])


@router.get("/metrics", summary="Prometheus telemetry scrape target")
async def metrics_endpoint():
    """Exposes real-time Prometheus metrics for scrapers."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health_check():
    """Returns 200 if the API service process is alive."""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc),
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    responses={
        status.HTTP_200_OK: {"description": "All backend dependencies healthy"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "One or more dependencies down"},
    },
)
async def readiness_check():
    """Checks reachability of backing dependencies: Redis, RabbitMQ, PostgreSQL.

    In early bootstrap or dev without running containers, reports status gracefully.
    """
    settings = get_settings()

    redis_ok = False
    rabbitmq_ok = False
    postgres_ok = False

    # Redis probe
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(settings.redis_url, socket_timeout=1.0)
        await client.ping()
        await client.aclose()
        redis_ok = True
    except Exception:
        redis_ok = False

    # RabbitMQ probe (TCP socket check)
    try:
        import socket
        from urllib.parse import urlparse
        parsed = urlparse(settings.rabbitmq_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5672
        with socket.create_connection((host, port), timeout=1.0):
            rabbitmq_ok = True
    except Exception:
        rabbitmq_ok = False

    # PostgreSQL probe
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        engine = create_async_engine(settings.database_url, connect_args={"timeout": 1.0})
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        postgres_ok = True
    except Exception:
        postgres_ok = False

    all_ready = redis_ok and rabbitmq_ok and postgres_ok
    status_str = "ok" if all_ready else ("degraded" if (redis_ok or rabbitmq_ok or postgres_ok) else "unavailable")

    response_data = ReadinessResponse(
        status=status_str,
        redis=redis_ok,
        rabbitmq=rabbitmq_ok,
        postgres=postgres_ok,
        timestamp=datetime.now(timezone.utc),
    )

    if not all_ready and settings.is_production:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=response_data.model_dump(mode="json"))

    return response_data
