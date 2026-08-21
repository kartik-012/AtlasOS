"""
AtlasOS Memory Write Service.

Orchestrates the complex write pipeline ensuring atomicity between
the PostgreSQL system-of-record, Qdrant vector index, and Knowledge Graph Mesh.
"""

from __future__ import annotations

import contextlib
import re
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger
from app.models.memory import EpisodicMemory, SemanticMemory
from app.repositories.memory import (
    ContradictionLogRepository,
    EpisodicMemoryRepository,
    SemanticMemoryRepository,
)
from app.repositories.tenant import TenantRepository
from app.services.contradiction import ContradictionService
from app.services.graph_service import EntityGraphService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.providers.base import EmbeddingProvider, NLIProvider
    from app.repositories.vector import VectorRepository

logger = get_logger(__name__)


class MemoryWriteService:
    """
    Service for writing memories and enriching knowledge graphs.
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
        self._graph_service = EntityGraphService(session)

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
        Write a raw episodic memory to the system, extract entity triples into Knowledge Graph Mesh.
        """
        settings = get_settings()
        memory_id = uuid.uuid4()
        now = int(datetime.now(UTC).timestamp())

        # 1. Generate Embedding
        vector = await self._embedding.get_embedding(content)

        # 2. Multi-Factor Importance Evaluation
        importance = self._calculate_multi_factor_importance(content)

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
                meta_data=metadata or {},
                importance_score=importance,
                vector_id=memory_id,
                source="api",
            )
            self._session.add(memory)
            await self._session.flush()

            # 5. Extract & Store Knowledge Graph Triples
            await self._graph_service.extract_and_store_triples(
                tenant_id=tenant_id,
                external_user_id=external_user_id,
                text=content,
                source_memory_id=memory_id,
                source_memory_type="episodic",
            )

            logger.info("episodic_memory_written", id=str(memory_id))
            return memory

        except Exception as e:
            logger.exception(
                "postgres_write_failed_rolling_back_qdrant",
                id=str(memory_id),
                error=str(e),
            )
            with contextlib.suppress(Exception):
                await self._vector_repo.delete_point(memory_id)
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
        Write a consolidated semantic memory (fact) with NLI contradiction checking & entity graph extraction.
        """
        settings = get_settings()
        tenant = await self._tenant_repo.get_by_id(tenant_id)
        if not tenant:
            raise ExternalServiceError(message="Tenant not found in context.")

        memory_id = uuid.uuid4()
        now = int(datetime.now(UTC).timestamp())

        # 1. Generate Embedding
        vector = await self._embedding.get_embedding(content)
        importance = self._calculate_multi_factor_importance(content)

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
                meta_data=metadata or {},
                importance_score=importance,
                vector_id=memory_id,
            )
            self._session.add(memory)
            await self._session.flush()

            # 5. Extract & Store Knowledge Graph Triples
            await self._graph_service.extract_and_store_triples(
                tenant_id=tenant_id,
                external_user_id=external_user_id,
                text=content,
                source_memory_id=memory_id,
                source_memory_type="semantic",
            )

            logger.info("semantic_memory_written", id=str(memory_id))
            return memory, has_contradiction, log_id

        except Exception as e:
            logger.exception("postgres_semantic_write_failed", error=str(e))
            with contextlib.suppress(Exception):
                await self._vector_repo.delete_point(memory_id)
            raise ExternalServiceError(
                message="Failed to write semantic memory.",
            ) from e

    def _calculate_multi_factor_importance(self, text: str) -> float:
        """
        Multi-Factor Importance Evaluator:
        - Base text length weight (0.2)
        - Salience keywords (preferences, names, dates, constraints) (0.5)
        - Specificity & Entity density (0.3)
        """
        base_score = min(len(text) / 500.0, 0.2)
        salience_keywords = [
            "always", "never", "prefer", "like", "dislike", "hate", "love",
            "must", "important", "crucial", "work", "live", "email", "phone",
        ]
        keyword_matches = sum(1 for kw in salience_keywords if re.search(rf"\b{kw}\b", text, re.IGNORECASE))
        salience_score = min(keyword_matches * 0.15, 0.5)

        # Entity density proxy (capitalized words / numbers)
        capitalized = len(re.findall(r"\b[A-Z][a-z]+\b", text))
        numbers = len(re.findall(r"\b\d+\b", text))
        density_score = min((capitalized + numbers) * 0.05, 0.3)

        total = 0.3 + base_score + salience_score + density_score
        return round(min(total, 1.0), 2)
