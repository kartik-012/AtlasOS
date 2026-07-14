"""
AtlasOS Memory Write Service.

Orchestrates the complex write pipeline ensuring atomicity between
the PostgreSQL system-of-record and the Qdrant vector index.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger
from app.models.memory import EpisodicMemory, SemanticMemory
from app.models.tenant import Tenant
from app.providers.base import EmbeddingProvider, NLIProvider
from app.repositories.memory import (
    ContradictionLogRepository,
    EpisodicMemoryRepository,
    SemanticMemoryRepository,
)
from app.repositories.tenant import TenantRepository
from app.repositories.vector import VectorRepository
from app.services.contradiction import ContradictionService

logger = get_logger(__name__)


class MemoryWriteService:
    """
    Service for writing memories.

    Dual-write strategy:
    1. Generate ID and create model instances.
    2. Generate embedding.
    3. Run NLI contradiction check (if semantic).
    4. Upsert to Qdrant.
    5. Flush to Postgres.
    6. If Postgres flush fails, fire compensating delete on Qdrant.
    """

    def __init__(
        self,
        session: AsyncSession,
        embedding_provider: EmbeddingProvider,
        nli_provider: NLIProvider,
        vector_repo: VectorRepository,
    ) -> None:
        self._session = session
        self._embedding = embedding_provider
        self._vector_repo = vector_repo

        self._episodic_repo = EpisodicMemoryRepository(session)
        self._semantic_repo = SemanticMemoryRepository(session)
        self._tenant_repo = TenantRepository(session)

        # Instantiate contradiction service
        log_repo = ContradictionLogRepository(session)
        self._contradiction_service = ContradictionService(
            nli_provider=nli_provider,
            vector_repo=vector_repo,
            semantic_repo=self._semantic_repo,
            log_repo=log_repo,
        )

    async def write_episodic(
        self,
        tenant_id: uuid.UUID,
        external_user_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> EpisodicMemory:
        """
        Write a raw episodic memory to the system.
        Episodic memories bypass contradiction checks because they are
        immutable observations of events.
        """
        settings = get_settings()
        memory_id = uuid.uuid4()
        now = int(datetime.now(timezone.utc).timestamp())

        # 1. Generate Embedding
        vector = await self._embedding.get_embedding(content)

        # 2. Heuristic Importance Score
        importance = self._calculate_base_importance(content)

        # 3. Upsert to Qdrant First
        await self._vector_repo.upsert_point(
            point_id=memory_id,
            vector=vector,
            tenant_id=tenant_id,
            external_user_id=external_user_id,
            memory_type="episodic",
            importance_score=importance,
            created_at=now,
        )

        # 4. Save to Postgres
        try:
            memory = EpisodicMemory(
                id=memory_id,
                tenant_id=tenant_id,
                external_user_id=external_user_id,
                content=content,
                embedding_model=settings.EMBEDDING_MODEL,
                metadata=metadata or {},
                importance_score=importance,
                vector_id=memory_id,
                source="api",
            )
            self._session.add(memory)
            await self._session.flush()

            logger.info("episodic_memory_written", id=str(memory_id))
            return memory

        except Exception as e:
            # Compensating transaction: attempt to remove orphaned Qdrant point
            logger.error(
                "postgres_write_failed_rolling_back_qdrant",
                id=str(memory_id),
                error=str(e),
            )
            try:
                await self._vector_repo.delete_point(memory_id)
            except Exception as cleanup_error:
                logger.critical(
                    "qdrant_rollback_failed",
                    id=str(memory_id),
                    error=str(cleanup_error),
                )
            raise ExternalServiceError(
                message="Failed to write episodic memory.",
            ) from e

    async def write_semantic(
        self,
        tenant_id: uuid.UUID,
        external_user_id: str,
        content: str,
        source_episodic_id: uuid.UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[SemanticMemory, bool, uuid.UUID | None]:
        """
        Write a consolidated semantic memory (fact).
        Executes the NLI contradiction pipeline.

        Returns:
            Tuple of (memory_object, contradiction_detected, log_id).
        """
        settings = get_settings()
        tenant = await self._tenant_repo.get_by_id(tenant_id)
        if not tenant:
            raise ExternalServiceError(message="Tenant not found in context.")

        memory_id = uuid.uuid4()
        now = int(datetime.now(timezone.utc).timestamp())

        # 1. Generate Embedding
        vector = await self._embedding.get_embedding(content)
        importance = self._calculate_base_importance(content)

        # 2. Contradiction Check
        has_contradiction, log_id = await self._contradiction_service.check_for_contradiction(
            tenant=tenant,
            external_user_id=external_user_id,
            new_fact_content=content,
            new_fact_vector=vector,
            new_fact_id=memory_id,
        )

        # 3. Upsert to Qdrant
        await self._vector_repo.upsert_point(
            point_id=memory_id,
            vector=vector,
            tenant_id=tenant_id,
            external_user_id=external_user_id,
            memory_type="semantic",
            importance_score=importance,
            created_at=now,
        )

        # 4. Save to Postgres
        try:
            memory = SemanticMemory(
                id=memory_id,
                tenant_id=tenant_id,
                external_user_id=external_user_id,
                content=content,
                embedding_model=settings.EMBEDDING_MODEL,
                source_episodic_id=source_episodic_id,
                metadata=metadata or {},
                importance_score=importance,
                vector_id=memory_id,
            )
            self._session.add(memory)
            await self._session.flush()

            logger.info("semantic_memory_written", id=str(memory_id))
            return memory, has_contradiction, log_id

        except Exception as e:
            logger.error("postgres_semantic_write_failed", error=str(e))
            try:
                await self._vector_repo.delete_point(memory_id)
            except Exception:
                pass
            raise ExternalServiceError(
                message="Failed to write semantic memory.",
            ) from e

    def _calculate_base_importance(self, text: str) -> float:
        """
        Simple heuristic for Phase 3.
        In production, an LLM call or dedicated lightweight model calculates this.
        """
        score = 0.5 + min(len(text) / 2000.0, 0.4)
        return round(score, 2)
