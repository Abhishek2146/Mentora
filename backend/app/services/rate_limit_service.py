"""
Redis-backed request rate limiter.

Fixed-window counter using atomic Redis operations (INCR + EXPIRE
executed inside a MULTI/EXEC pipeline) so concurrent requests can
never race past the limit.

Follows the same fail-open convention as the existing token
blacklist service: if Redis is unavailable, requests are allowed.
"""

import time
from typing import Optional, Tuple

import redis.asyncio as redis

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

RATE_LIMIT_MESSAGE = "Too many requests. Please try again later."


class RateLimiter:
    """Atomic fixed-window rate limiter backed by Redis."""

    WINDOW_SECONDS: int = 60

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._is_available: bool = True
        self._connect()

    def _connect(self) -> None:
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            self._is_available = True
        except Exception:
            self.redis_client = None
            self._is_available = False

    def _build_key(self, identifier: str) -> str:
        """Bucket key for the current fixed time window."""
        window = int(time.time()) // self.WINDOW_SECONDS
        return f"ratelimit:{identifier}:{window}"

    async def check(
        self,
        identifier: str,
        limit: int,
        window_seconds: Optional[int] = None,
    ) -> Tuple[bool, int]:
        """
        Atomically count a request and decide whether it is allowed.

        Args:
            identifier: Primary limiter key (e.g. "user:42" or "ip:1.2.3.4").
            limit: Max requests allowed within the window (<= 0 means unlimited).
            window_seconds: Optional custom window size.

        Returns:
            (allowed, retry_after_seconds). retry_after is 0 when allowed.
            Fails open (allowed=True) when Redis is unreachable.
        """

        window = window_seconds or self.WINDOW_SECONDS

        if not settings.USER_RATE_LIMIT_ENABLED or limit <= 0:
            return True, 0

        if not self.redis_client or not self._is_available:
            return True, 0

        key = self._build_key(identifier)

        try:
            # INCR + EXPIRE run atomically inside a transaction pipeline,
            # preventing race conditions between simultaneous requests.
            pipe = self.redis_client.pipeline(transaction=True)
            pipe.incr(key)
            pipe.expire(key, window)
            results = await pipe.execute()
            count = int(results[0])

            if count > limit:
                retry_after = max(
                    1,
                    window - (int(time.time()) % window),
                )
                logger.warning(
                    "Rate limit exceeded for '%s' (%d/%d)",
                    identifier,
                    count,
                    limit,
                )
                return False, retry_after

            return True, 0

        except Exception as exc:
            # Fail open — matches the token blacklist behaviour.
            self._is_available = False
            logger.warning("Rate limiter unavailable, failing open: %s", exc)
            return True, 0

    async def reset(self, identifier: str) -> None:
        """Clear all window buckets for an identifier (mainly for tests)."""
        if not self.redis_client or not self._is_available:
            return
        try:
            keys = []
            async for key in self.redis_client.scan_iter(
                f"ratelimit:{identifier}:*"
            ):
                keys.append(key)
            if keys:
                await self.redis_client.delete(*keys)
        except Exception:
            pass


rate_limiter = RateLimiter()
