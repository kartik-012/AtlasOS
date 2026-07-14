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

import uuid
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as rest

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# The single unified collection for all vector data in AtlasOS.
COLLECTION_NAME = "atlas_memories"


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
            # Use gRPC if available for performance
            grpc_port=6334,
            prefer_grpc=True,
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
        """
        Upsert a single vector point.

        Args:
            point_id: UUID matching the PostgreSQL record ID.
            vector: The dense embedding vector.
            tenant_id: Must match the PostgreSQL tenant_id.
            external_user_id: The external user this memory belongs to.
            memory_type: 'episodic' or 'semantic'.
            importance_score: For fast ranking.
            created_at: Unix timestamp.
            additional_payload: Any extra metadata.
        """
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
    ) -> list[rest.ScoredPoint]:
        """
        Search for nearest neighbors with mandatory tenant/user filters.

        Args:
            query_vector: The embedded query.
            tenant_id: Filter to enforce tenant isolation.
            external_user_id: Filter to enforce user isolation.
            memory_type: Optional filter by type.
            limit: Max results.
            score_threshold: Optional cosine similarity minimum threshold.

        Returns:
            List of ScoredPoint objects from Qdrant.
        """
        # Build mandatory filter conditions
        conditions = [
            rest.FieldCondition(
                key="tenant_id", match=rest.MatchValue(value=str(tenant_id))
            ),
            rest.FieldCondition(
                key="external_user_id", match=rest.MatchValue(value=external_user_id)
            ),
        ]

        if memory_type:
            conditions.append(
                rest.FieldCondition(
                    key="memory_type", match=rest.MatchValue(value=memory_type)
                )
            )

        query_filter = rest.Filter(must=conditions)

        # Execute search
        results = await self.client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
            with_vectors=False,
        )

        return results

    async def delete_point(self, point_id: uuid.UUID) -> None:
        """
        Delete a point by ID.
        """
        await self.client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=rest.PointIdsList(points=[str(point_id)]),
        )

    async def close(self) -> None:
        """Close the underlying client."""
        await self.client.close()
