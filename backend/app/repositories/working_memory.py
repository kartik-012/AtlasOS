"""
AtlasOS Redis Working Memory Repository.

Provides ephemeral "Working Memory" capabilities for agents.
Working memory tracks the current task state, recent messages, and
short-term context in Redis, expiring automatically after a TTL.

Keys structure:
  wm:{tenant_id}:{external_user_id}:{session_id} -> Hash Map
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class WorkingMemoryRepository:
    """
    Repository for interacting with Redis for Working Memory.
    """

    def __init__(self) -> None:
        settings = get_settings()
        import redis.asyncio as aioredis

        self.redis = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
        self.ttl_seconds = 7200  # 2 hours

    def _make_key(
        self,
        tenant_id: uuid.UUID,
        external_user_id: str,
        session_id: str,
    ) -> str:
        return f"wm:{tenant_id}:{external_user_id}:{session_id}"

    async def get_state(
        self,
        tenant_id: uuid.UUID,
        external_user_id: str,
        session_id: str,
    ) -> dict[str, Any]:
        """
        Retrieve the current working memory state for a session.
        """
        key = self._make_key(tenant_id, external_user_id, session_id)
        data = await self.redis.hgetall(key)
        
        # Parse nested JSON strings if any
        parsed = {}
        for k, v in data.items():
            try:
                parsed[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                parsed[k] = v
        return parsed

    async def update_state(
        self,
        tenant_id: uuid.UUID,
        external_user_id: str,
        session_id: str,
        updates: dict[str, Any],
    ) -> None:
        """
        Update the working memory state with new keys/values.
        Resets the TTL.
        """
        key = self._make_key(tenant_id, external_user_id, session_id)
        
        # Serialize nested dicts/lists to JSON strings for Redis hash storage
        serialized = {}
        for k, v in updates.items():
            if isinstance(v, (dict, list)):
                serialized[k] = json.dumps(v)
            else:
                serialized[k] = str(v)

        if serialized:
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.hset(key, mapping=serialized)
                pipe.expire(key, self.ttl_seconds)
                # Keep an index of active sessions per user for quick cleanup
                idx_key = f"wm:idx:{tenant_id}:{external_user_id}"
                pipe.sadd(idx_key, session_id)
                pipe.expire(idx_key, self.ttl_seconds)
                await pipe.execute()

    async def delete_state(
        self,
        tenant_id: uuid.UUID,
        external_user_id: str,
        session_id: str,
    ) -> None:
        """
        Clear the working memory for a specific session.
        """
        key = self._make_key(tenant_id, external_user_id, session_id)
        idx_key = f"wm:idx:{tenant_id}:{external_user_id}"
        
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.delete(key)
            pipe.srem(idx_key, session_id)
            await pipe.execute()

    async def get_active_sessions(
        self,
        tenant_id: uuid.UUID,
        external_user_id: str,
    ) -> list[str]:
        """
        List all active working memory session IDs for a user.
        """
        idx_key = f"wm:idx:{tenant_id}:{external_user_id}"
        members = await self.redis.smembers(idx_key)
        return list(members)

    async def close(self) -> None:
        """Close the Redis connection pool."""
        await self.redis.aclose()
