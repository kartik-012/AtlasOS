"""
AtlasOS Qdrant Vector Repository.

Manages operations against the Qdrant vector database.
The `atlas_memories` collection stores both episodic and semantic
memories, differentiated by the `memory_type` payload field.

Payload schema for fast filtering:
  - tenant_id (UUID string)
  - external_user_id (string)
  - memory_type (string: 'episodic' | 'semantic')
  - importance_score (float)
  - created_at (int, unix timestamp)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx
from qdrant_client import AsyncQdrantClient, models as rest

from app.core.config import get_settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    import uuid

logger = get_logger(__name__)

# The single unified collection for all vector data in AtlasOS.
COLLECTION_NAME = "atlas_memories"


@dataclass
class ScoredPoint:
    id: str
    score: float
    payload: dict[str, Any]


class VectorRepository:
    """
    Repository for interacting with the Qdrant vector database.

    Provides methods for upserting points, searching by similarity with
    mandatory payload filters, and deleting points.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.client = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
            check_compatibility=False,
        )

    async def initialize_collection(self, dimension: int = 1024) -> None:
        """
        Create the collection and indexes if it does not exist.
        Called during app startup or migration.
        """
        exists = await self.client.collection_exists(COLLECTION_NAME)
        if not exists:
            logger.info("creating_qdrant_collection", name=COLLECTION_NAME, dim=dimension)
            await self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=rest.VectorParams(
                    size=dimension,
                    distance=rest.Distance.COSINE,
                ),
            )
            # Create payload indexes for fast filtering
            await self.client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="tenant_id",
                field_schema=rest.PayloadSchemaType.KEYWORD,
            )
            await self.client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="external_user_id",
                field_schema=rest.PayloadSchemaType.KEYWORD,
            )
            await self.client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="memory_type",
                field_schema=rest.PayloadSchemaType.KEYWORD,
            )

    async def upsert_point(
        self,
        point_id: uuid.UUID,
        vector: list[float],
        tenant_id: uuid.UUID,
        external_user_id: str,
        memory_type: str,
        importance_score: float,
        created_at: int,
        additional_payload: dict[str, Any] | None = None,
    ) -> None:
        """Upsert a single vector point."""
        payload = {
            "tenant_id": str(tenant_id),
            "external_user_id": external_user_id,
            "memory_type": memory_type,
            "importance_score": importance_score,
            "created_at": created_at,
        }
        if additional_payload:
            payload.update(additional_payload)

        point = rest.PointStruct(
            id=str(point_id),
            vector=vector,
            payload=payload,
        )

        await self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=[point],
        )

    async def search(
        self,
        query_vector: list[float],
        tenant_id: uuid.UUID,
        external_user_id: str,
        memory_type: str | None = None,
        limit: int = 10,
        score_threshold: float | None = None,
    ) -> list[ScoredPoint]:
        """
        Search for nearest neighbors with mandatory tenant/user filters.
        """
        must_conditions: list[dict[str, Any]] = [
            {"key": "tenant_id", "match": {"value": str(tenant_id)}},
            {"key": "external_user_id", "match": {"value": external_user_id}},
        ]
        if memory_type:
            must_conditions.append({"key": "memory_type", "match": {"value": memory_type}})

        body: dict[str, Any] = {
            "vector": query_vector,
            "filter": {"must": must_conditions},
            "limit": limit,
            "with_payload": True,
            "with_vector": False,
        }
        if score_threshold is not None:
            body["score_threshold"] = score_threshold

        settings = get_settings()
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(
                f"{settings.QDRANT_URL.rstrip('/')}/collections/{COLLECTION_NAME}/points/search",
                json=body,
            )
            res.raise_for_status()
            data = res.json().get("result", [])
            return [
                ScoredPoint(
                    id=str(item.get("id")),
                    score=float(item.get("score", 0.0)),
                    payload=item.get("payload") or {},
                )
                for item in data
            ]

    async def delete_point(self, point_id: uuid.UUID) -> None:
        """Delete a point by ID."""
        await self.client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=rest.PointIdsList(points=[str(point_id)]),
        )

    async def close(self) -> None:
        """Close the underlying client."""
        await self.client.close()
