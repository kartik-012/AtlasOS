"""
AtlasOS Memory Read Service.

Retrieval Query Engine. Combines vector similarity from Qdrant with
Importance Scores stored in the payload to generate a composite ranking.
Hydrates the top-K results from PostgreSQL.
"""

from __future__ import annotations

import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.providers.base import EmbeddingProvider
from app.repositories.memory import EpisodicMemoryRepository, SemanticMemoryRepository
from app.repositories.vector import VectorRepository
from app.schemas.memory import MemorySearchResponse, ScoredMemoryResult

logger = get_logger(__name__)


class MemoryReadService:
    """
    Service for executing retrieval queries.
    """

    def __init__(
        self,
        session: AsyncSession,
        embedding_provider: EmbeddingProvider,
        vector_repo: VectorRepository,
    ) -> None:
        self._session = session
        self._embedding = embedding_provider
        self._vector_repo = vector_repo

        self._episodic_repo = EpisodicMemoryRepository(session)
        self._semantic_repo = SemanticMemoryRepository(session)

        # Composite ranking weights
        self.w_sim = 0.75  # Weight for Cosine Similarity
        self.w_imp = 0.25  # Weight for Importance Score

    async def search(
        self,
        tenant_id: uuid.UUID,
        external_user_id: str,
        query: str,
        memory_type: str | None = None,
        limit: int = 10,
        score_threshold: float | None = None,
    ) -> MemorySearchResponse:
        """
        Execute the full read pipeline.
        """
        start_time = time.perf_counter()

        # 1. Embed Query
        query_vector = await self._embedding.get_embedding(query)

        # 2. Qdrant Search — fetch more candidates than needed for re-ranking
        fetch_limit = min(limit * 3, 100)

        raw_results = await self._vector_repo.search(
            query_vector=query_vector,
            tenant_id=tenant_id,
            external_user_id=external_user_id,
            memory_type=memory_type,
            limit=fetch_limit,
            score_threshold=score_threshold,
        )

        if not raw_results:
            return MemorySearchResponse(
                results=[],
                query_time_ms=(time.perf_counter() - start_time) * 1000,
            )

        # 3. Composite Re-Ranking
        ranked_candidates = []
        for point in raw_results:
            sim_score = point.score
            imp_score = point.payload.get("importance_score", 0.5) if point.payload else 0.5

            # Formula: w1 * Similarity + w2 * Importance
            composite = (self.w_sim * sim_score) + (self.w_imp * imp_score)

            ranked_candidates.append({
                "id": uuid.UUID(point.id),
                "type": point.payload.get("memory_type") if point.payload else "unknown",
                "sim": sim_score,
                "imp": imp_score,
                "comp": composite,
            })

        # Sort by composite score descending
        ranked_candidates.sort(key=lambda x: x["comp"], reverse=True)

        # Slice to requested limit
        top_k = ranked_candidates[:limit]

        # 4. Hydrate from PostgreSQL
        ep_ids = [c["id"] for c in top_k if c["type"] == "episodic"]
        sem_ids = [c["id"] for c in top_k if c["type"] == "semantic"]

        ep_memories = await self._episodic_repo.get_by_ids(tenant_id, ep_ids)
        sem_memories = await self._semantic_repo.get_by_ids(tenant_id, sem_ids)

        # Build lookup dict
        db_memories: dict[uuid.UUID, object] = {}
        for em in ep_memories:
            db_memories[em.id] = em
        for sm in sem_memories:
            if sm.superseded_by is None:
                db_memories[sm.id] = sm

        # 5. Format Output
        final_results = []
        for cand in top_k:
            db_record = db_memories.get(cand["id"])
            if not db_record:
                continue

            final_results.append(
                ScoredMemoryResult(
                    id=db_record.id,
                    memory_type=cand["type"],
                    content=db_record.content,
                    metadata=db_record.metadata or {},
                    importance_score=cand["imp"],
                    similarity_score=cand["sim"],
                    composite_score=cand["comp"],
                    created_at=db_record.created_at,
                )
            )

            # Increment access counts
            if cand["type"] == "episodic":
                await self._episodic_repo.increment_access_count(db_record.id)
            else:
                await self._semantic_repo.increment_access_count(db_record.id)

        query_time = (time.perf_counter() - start_time) * 1000
        logger.info(
            "memory_search_completed",
            tenant_id=str(tenant_id),
            results=len(final_results),
            time_ms=query_time,
        )

        return MemorySearchResponse(
            results=final_results,
            query_time_ms=query_time,
        )
