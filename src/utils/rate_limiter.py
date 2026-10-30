"""
EchoAgent — Redis Sliding Window Rate Limiter
Prevents API flooding and brute force using atomic Redis sorted sets.
"""

import time
import structlog
from redis.asyncio import Redis

logger = structlog.get_logger(__name__)


class SlidingWindowRateLimiter:
    """Sliding window log rate limiter using Redis sorted sets."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int, int]:
        """Check if request is allowed under the rate limit.

        Args:
            key: Unique identifier (e.g., "ratelimit:ip:127.0.0.1")
            max_requests: Maximum allowed requests in the time window
            window_seconds: Time window duration in seconds

        Returns:
            Tuple of (allowed: bool, remaining_requests: int, retry_after_seconds: int)
        """
        now = time.time()
        window_start = now - window_seconds
        member = f"{now}:{time.time_ns()}"

        try:
            pipe = self.redis.pipeline(transaction=True)
            # 1. Remove expired timestamps outside the sliding window
            pipe.zremrangebyscore(key, 0, window_start)
            # 2. Add current request timestamp
            pipe.zadd(key, {member: now})
            # 3. Count requests in current window
            pipe.zcard(key)
            # 4. Set TTL on the key so it self-cleans
            pipe.expire(key, window_seconds * 2)

            results = await pipe.execute()
            current_count = results[2]

            if current_count > max_requests:
                # Calculate when the oldest request in the window expires
                oldest = await self.redis.zrange(key, 0, 0, withscores=True)
                retry_after = int(window_seconds - (now - oldest[0][1])) if oldest else window_seconds
                return False, 0, max(1, retry_after)

            remaining = max(0, max_requests - current_count)
            return True, remaining, 0

        except Exception as exc:
            # Fail open if Redis is down, but log warning
            logger.warning("rate_limiter_redis_error", key=key, error=str(exc))
            return True, max_requests, 0

