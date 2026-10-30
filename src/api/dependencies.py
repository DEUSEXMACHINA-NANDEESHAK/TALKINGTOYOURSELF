"""
EchoAgent — API Dependencies
Dependency injection providers for Redis, DB, Rate Limiter, and Session context.
"""

from typing import AsyncGenerator
import redis.asyncio as aioredis
from fastapi import Depends, Header, HTTPException, Request, status

from src.core.config import get_settings
from src.core.constants import (
    RATE_LIMIT_MAX_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
    REDIS_RATELIMIT_PREFIX,
)
from src.utils.rate_limiter import SlidingWindowRateLimiter

_redis_pool: aioredis.ConnectionPool | None = None


def get_redis_pool() -> aioredis.ConnectionPool:
    """Return singleton Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        settings = get_settings()
        _redis_pool = aioredis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            decode_responses=True,
        )
    return _redis_pool


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """FastAPI dependency to yield an async Redis client."""
    pool = get_redis_pool()
    client = aioredis.Redis(connection_pool=pool)
    try:
        yield client
    finally:
        await client.aclose()


async def check_rate_limit(
    request: Request,
    redis: aioredis.Redis = Depends(get_redis),
    x_forwarded_for: str | None = Header(default=None),
) -> None:
    """Dependency that enforces sliding window rate limiting per client IP."""
    settings = get_settings()
    if settings.debug:
        return

    # Extract client IP (respecting proxy headers)
    client_ip = (
        x_forwarded_for.split(",")[0].strip()
        if x_forwarded_for
        else (request.client.host if request.client else "127.0.0.1")
    )

    rate_key = f"{REDIS_RATELIMIT_PREFIX}ip:{client_ip}"
    limiter = SlidingWindowRateLimiter(redis)
    allowed, remaining, retry_after = await limiter.is_allowed(
        key=rate_key,
        max_requests=RATE_LIMIT_MAX_REQUESTS,
        window_seconds=RATE_LIMIT_WINDOW_SECONDS,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please slow down.",
            headers={"Retry-After": str(retry_after)},
        )
