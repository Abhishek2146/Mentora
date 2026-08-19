"""
Token Blacklist Service for server-side JWT revocation.
"""
import redis.asyncio as redis
from typing import Optional

from app.core.config import settings


class TokenBlacklist:
    """Service for managing revoked JWT tokens."""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._connect()

    def _connect(self):
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
        except Exception:
            self.redis_client = None

    async def add_token(self, token: str, expires_in: int) -> bool:
        """
        Add a token to the blacklist.

        Args:
            token: JWT token to blacklist
            expires_in: Token TTL in seconds

        Returns:
            True if added successfully, False otherwise
        """
        if not self.redis_client:
            return False
        try:
            await self.redis_client.setex(
                f"blacklist:{token}",
                expires_in,
                "1"
            )
            return True
        except Exception:
            return False

    async def is_blacklisted(self, token: str) -> bool:
        """
        Check if a token is blacklisted.

        Args:
            token: JWT token to check

        Returns:
            True if blacklisted, False otherwise
        """
        if not self.redis_client:
            return False
        try:
            result = await self.redis_client.get(f"blacklist:{token}")
            return result is not None
        except Exception:
            return False

    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()


token_blacklist = TokenBlacklist()