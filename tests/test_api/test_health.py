"""
EchoAgent — Health Endpoint Tests
"""

import pytest


@pytest.mark.asyncio
async def test_health_check_returns_200(client):
    """Liveness probe must always return 200 and healthy status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
    assert "timestamp" in data
    assert "X-Request-ID" in response.headers
    assert "X-Response-Time-Ms" in response.headers


@pytest.mark.asyncio
async def test_readiness_check_endpoint(client):
    """Readiness probe returns status and breakdown of backing services."""
    response = await client.get("/ready")
    # In development/test without live containers, it should return 200 with degraded/unavailable flags
    assert response.status_code in [200, 503]
    data = response.json()
    assert "status" in data
    assert "redis" in data
    assert "rabbitmq" in data
    assert "postgres" in data


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_prometheus_format(client):
    """Prometheus /metrics endpoint returns 200 and text/plain telemetry."""
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert len(response.text) > 0
