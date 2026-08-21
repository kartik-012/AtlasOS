"""
AtlasOS Redis Client & Key Namespace Management.

Provides an async Redis client factory, FastAPI dependency, and a structured
key namespace for all Redis operations.

Redis serves four distinct roles in AtlasOS:
  1. Working Memory Store: Short-lived agent task state (Hash, 2h TTL).
  2. Session Cache: Console session data cache (String/JSON, 30min TTL).
  3. Rate Limiting: Per-API-key request counters (String/Counter, 90s TTL).
  4. Celery Broker/Backend: Task message queue and result store.

Design decisions:
  - Separate databases (DB 0-3) isolate concerns and simplify debugging.
  - Key prefix constants ensure consistent naming across the codebase.
  - The RedisKeyBuilder class constructs keys with proper namespacing,
    preventing accidental key collisions.
  - Connection pool (max_connections=50) is sized for a single backend
    instance. Scale horizontally by adding backend replicas, not by
    increasing the pool size beyond what a single Redis server can handle.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import redis.asyncio as aioredis

from app.core.config import get_settings

if TYPE_CHECKING:
    import uuid
    from collections.abc import AsyncGenerator


class RedisKeyBuilder:
    """
    Constructs properly namespaced Redis keys.

    All keys follow the pattern: {prefix}:{tenant_id}:{...identifiers}

    This class is a pure utility — it has no state beyond the key patterns.
    Using a class instead of bare functions groups related key-building
    logic and makes the key namespace self-documenting.
    """

    # Working memory: stores ephemeral agent task state
    WM_PREFIX = "wm"
    # Working memory session index: tracks active sessions per user
    WM_INDEX_PREFIX = "wm:idx"
    # Console session cache: caches session data from PostgreSQL
    SESSION_PREFIX = "session"
    # Rate limiting: per-minute request counters
    RATE_LIMIT_PREFIX = "ratelimit"
    # Rate limiting: token bucket burst counters
    RATE_LIMIT_BURST_PREFIX = "ratelimit:burst"

    # TTLs in seconds
    WM_TTL: int = 7200  # 2 hours
    SESSION_TTL: int = 1800  # 30 minutes
    RATE_LIMIT_TTL: int = 90
    RATE_LIMIT_BURST_TTL: int = 10

    @staticmethod
    def working_memory(
        tenant_id: uuid.UUID,
        external_user_id: str,
        session_id: str,
    ) -> str:
        """Build a working memory key for a specific agent session."""
        return f"{RedisKeyBuilder.WM_PREFIX}:{tenant_id}:{external_user_id}:{session_id}"

    @staticmethod
    def working_memory_index(
        tenant_id: uuid.UUID,
        external_user_id: str,
    ) -> str:
        """Build a working memory session index key for a user."""
        return f"{RedisKeyBuilder.WM_INDEX_PREFIX}:{tenant_id}:{external_user_id}"

    @staticmethod
    def session_cache(session_id: uuid.UUID) -> str:
        """Build a session cache key."""
        return f"{RedisKeyBuilder.SESSION_PREFIX}:{session_id}"

    @staticmethod
    def rate_limit(api_key_id: uuid.UUID, minute_bucket: int) -> str:
        """Build a rate limit counter key for a specific minute."""
        return f"{RedisKeyBuilder.RATE_LIMIT_PREFIX}:{api_key_id}:{minute_bucket}"

    @staticmethod
    def rate_limit_burst(api_key_id: uuid.UUID) -> str:
        """Build a rate limit burst counter key."""
        return f"{RedisKeyBuilder.RATE_LIMIT_BURST_PREFIX}:{api_key_id}"


class RedisClient:
    """
    Async Redis client wrapper with structured helper methods.

    Wraps redis.asyncio.Redis to provide typed JSON get/set operations
    and atomic counter management. These helpers reduce boilerplate
    and enforce consistent serialization across the codebase.
    """

    def __init__(self, client: aioredis.Redis) -> None:
        self._client = client

    @property
    def client(self) -> aioredis.Redis:
        """Access the underlying redis.asyncio.Redis client."""
        return self._client

    async def get_json(self, key: str) -> Any | None:
        """
        Get a key and deserialize its value from JSON.

        Returns None if the key does not exist, matching the Redis GET
        behavior rather than raising an exception.
        """
        value = await self._client.get(key)
        if value is None:
            return None
        return json.loads(value)

    async def set_json(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """
        Serialize a value to JSON and store it with an optional TTL.

        Args:
            key: Redis key.
            value: Any JSON-serializable Python object.
            ttl: Time-to-live in seconds. None means no expiry.
        """
        serialized = json.dumps(value, default=str)
        if ttl is not None:
            await self._client.setex(key, ttl, serialized)
        else:
            await self._client.set(key, serialized)

    async def increment_counter(
        self,
        key: str,
        ttl: int | None = None,
    ) -> int:
        """
        Atomically increment a counter key and optionally set TTL.

        Uses a Redis pipeline to make INCR + EXPIRE atomic.
        Returns the new counter value after increment.
        """
        pipe = self._client.pipeline(transaction=True)
        pipe.incr(key)
        if ttl is not None:
            pipe.expire(key, ttl)
        results = await pipe.execute()
        # INCR result is the first element in the pipeline response
        return int(results[0])

    async def close(self) -> None:
        """Close the Redis connection pool."""
        await self._client.aclose()


def create_redis_client() -> RedisClient:
    """
    Create a new RedisClient instance from application settings.

    The connection pool (max_connections=50) is sized for a single backend
    instance handling concurrent requests. Each request that needs Redis
    acquires a connection from the pool, uses it, and returns it.

    decode_responses=True: Redis returns bytes by default. Enabling decode
    converts all responses to strings, which is what we want for JSON
    serialization and key operations.
    """
    settings = get_settings()
    client = aioredis.from_url(  # type: ignore
        settings.REDIS_URL,
        max_connections=50,
        decode_responses=True,
        health_check_interval=30,
    )
    return RedisClient(client=client)


async def get_redis() -> AsyncGenerator[RedisClient, None]:
    """
    FastAPI dependency that provides a RedisClient.

    Creates a client per-request. In production, consider using a
    module-level client with connection pooling for better performance.
    The current design prioritizes correctness and clean teardown.

    Yields:
        RedisClient: An async Redis client wrapper.
    """
    redis_client = create_redis_client()
    try:
        yield redis_client
    finally:
        await redis_client.close()
