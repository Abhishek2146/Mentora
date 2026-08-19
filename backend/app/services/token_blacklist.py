"""
Token Blacklist Service for server-side JWT revocation.
"""
import redis.asyncio as redis
from typing import Optional
import asyncio

from app.core.config import settings


class TokenBlacklist:
    """Service for managing revoked JWT tokens."""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._is_available: bool = True
        self._connect()

    def _connect(self):
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

    async def add_token(self, token: str, expires_in: int) -> bool:
        """
        Add a token to the blacklist.

        Args:
            token: JWT token to blacklist
            expires_in: Token TTL in seconds

        Returns:
            True if added successfully, False otherwise
        """
        if not self.redis_client or not self._is_available:
            return False
        try:
            await self.redis_client.setex(
                f"blacklist:{token}",
                expires_in,
                "1"
            )
            return True
        except Exception:
            self._is_available = False
            return False

    async def is_blacklisted(self, token: str) -> bool:
        """
        Check if a token is blacklisted.

        Args:
            token: JWT token to check

        Returns:
            True if blacklisted, False otherwise
        """
        if not self.redis_client or not self._is_available:
            return False
        try:
            result = await asyncio.wait_for(
                self.redis_client.get(f"blacklist:{token}"),
                timeout=2
            )
            return result is not None
        except Exception:
            self._is_available = False
            return False

    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()


token_blacklist = TokenBlacklist()