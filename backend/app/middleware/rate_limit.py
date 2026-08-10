"""
Middleware - Rate limiting
"""
import time
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_history = {}

    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        client_host = request.client.host
        current_time = time.time()

        if client_host not in self.request_history:
            self.request_history[client_host] = []

        self.request_history[client_host] = [
            t for t in self.request_history[client_host]
            if current_time - t < 60
        ]

        if len(self.request_history[client_host]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {client_host}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
            )

        self.request_history[client_host].append(current_time)
        return await call_next(request)
