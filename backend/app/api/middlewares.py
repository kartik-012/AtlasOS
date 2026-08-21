"""
AtlasOS API Middleware.

Provides production-grade middleware for:
  1. Rate Limiting: Redis-backed sliding window rate limiter per API key/user.
  2. Exception Handling: Translates AtlasOSError hierarchy into consistent
     JSON error responses.

Design decisions:
  - Rate limiting is implemented as ASGI middleware for maximum coverage.
    It intercepts requests BEFORE they reach the route handler, preventing
    resource waste on rate-limited requests.
  - The exception handler is registered as a FastAPI exception handler
    (not middleware) for proper integration with FastAPI's error handling.
  - Health check endpoints bypass rate limiting entirely.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from fastapi.responses import ORJSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import get_settings
from app.core.exceptions import AtlasOSError
from app.core.logging import get_logger

if TYPE_CHECKING:
    from fastapi import FastAPI, Request
    from starlette.responses import Response

logger = get_logger(__name__)


# =============================================================================
# Exception Handler
# =============================================================================


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register global exception handlers on the FastAPI application.

    Catches all AtlasOSError subclasses and formats them as consistent
    JSON error responses. Catches unhandled exceptions and returns a
    generic 500 error.
    """

    @app.exception_handler(AtlasOSError)
    async def atlas_error_handler(
        request: Request,
        exc: AtlasOSError,
    ) -> ORJSONResponse:
        """Handle all AtlasOS application errors."""
        logger.warning(
            "application_error",
            error_code=exc.error_code,
            status_code=exc.status_code,
            message=exc.message,
            path=str(request.url.path),
            method=request.method,
        )
        return ORJSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(
        request: Request,
        exc: Exception,
    ) -> ORJSONResponse:
        """Handle unexpected/unhandled exceptions."""
        logger.exception(
            "unhandled_error",
            path=str(request.url.path),
            method=request.method,
            error=str(exc),
        )
        settings = get_settings()
        detail = {"error": str(exc)} if settings.is_development else {}
        return ORJSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "ATLAS_INTERNAL_ERROR",
                    "message": "An unexpected internal error occurred.",
                    **detail,
                },
                "status_code": 500,
            },
        )


# =============================================================================
# Rate Limiting Middleware
# =============================================================================

# Paths that bypass rate limiting entirely
_RATE_LIMIT_EXEMPT_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Redis-backed sliding window rate limiter.

    Limits are applied per-client based on:
      - API Key: Uses the key prefix as the rate limit identifier.
      - JWT User: Uses the user ID from the token.
      - Anonymous: Uses the client IP address.

    The middleware uses a simple fixed-window counter strategy with
    Redis INCR + EXPIRE for atomic counter management. This is simpler
    than a true sliding window but sufficient for production use.

    Rate limit headers are added to every response:
      - X-RateLimit-Limit: Maximum requests per window.
      - X-RateLimit-Remaining: Requests remaining in current window.
      - X-RateLimit-Reset: Unix timestamp when the window resets.
    """

    def __init__(
        self,
        app: Any,
        requests_per_minute: int = 60,
    ) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process the request through rate limiting."""
        # Skip rate limiting for exempt paths
        if request.url.path in _RATE_LIMIT_EXEMPT_PATHS:
            return await call_next(request)

        # Extract rate limit identifier
        identifier = self._get_identifier(request)
        window = int(time.time() // 60)  # 1-minute window
        rate_key = f"ratelimit:{identifier}:{window}"

        try:
            # Import here to avoid circular imports at module level
            import redis.asyncio as aioredis

            settings = get_settings()
            redis_client = aioredis.from_url(  # type: ignore
                settings.REDIS_URL,
                decode_responses=True,
            )

            try:
                pipe = redis_client.pipeline(transaction=True)
                pipe.incr(rate_key)
                pipe.expire(rate_key, 90)  # TTL slightly longer than window
                results = await pipe.execute()
                current_count = int(results[0])
            finally:
                await redis_client.aclose()

            # Calculate remaining requests
            remaining = max(0, self.requests_per_minute - current_count)
            reset_time = (window + 1) * 60

            # Check if rate limited
            if current_count > self.requests_per_minute:
                logger.warning(
                    "rate_limit_exceeded",
                    identifier=identifier,
                    count=current_count,
                    limit=self.requests_per_minute,
                )
                return ORJSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "ATLAS_RATE_LIMITED",
                            "message": "Rate limit exceeded. Please try again later.",
                        },
                        "status_code": 429,
                    },
                    headers={
                        "X-RateLimit-Limit": str(self.requests_per_minute),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_time),
                        "Retry-After": str(reset_time - int(time.time())),
                    },
                )

            # Process request and add rate limit headers
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_time)
            return response

        except Exception:
            # If Redis is down, allow the request through (fail-open)
            # This prevents Redis outages from taking down the API
            logger.warning("rate_limiter_redis_unavailable", exc_info=True)
            return await call_next(request)

    @staticmethod
    def _get_identifier(request: Request) -> str:
        """
        Extract the rate limit identifier from the request.

        Priority: API Key prefix > JWT user ID > Client IP.
        """
        # Check for API key
        api_key = request.headers.get("X-API-Key")
        if api_key and len(api_key) >= 8:
            return f"key:{api_key[:8]}"

        # Check for JWT (extract user ID without full validation)
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            try:
                token = auth[7:]
                # Lightweight decode — just extract sub claim
                import base64
                import json

                parts = token.split(".")
                if len(parts) >= 2:
                    # Pad the base64 string
                    payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
                    payload = json.loads(base64.urlsafe_b64decode(payload_b64))
                    user_id = payload.get("sub")
                    if user_id:
                        return f"user:{user_id}"
            except Exception:
                pass

        # Fall back to client IP
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
