"""
AtlasOS Memory Read Service.

Retrieval Query Engine featuring:
1. Vector similarity from Qdrant.
2. Ebbinghaus retrievability decay: R(t) = e^(-dt / (S * (1 + access_count))).
3. Reciprocal Rank Fusion (RRF) combining dense similarity & importance scores.
4. Multi-hop Knowledge Graph Context Expansion.
"""

from __future__ import annotations

import math
import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.core.logging import get_logger
from app.repositories.graph import EntityGraphRepository
from app.repositories.memory import EpisodicMemoryRepository, SemanticMemoryRepository
from app.schemas.memory import MemorySearchResponse, ScoredMemoryResult
from app.services.graph_service import EntityGraphService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.providers.base import EmbeddingProvider
    from app.repositories.vector import VectorRepository

logger = get_logger(__name__)


class MemoryReadService:
    """
    Service for executing advanced multi-modal memory retrieval queries.
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
        self._graph_repo = EntityGraphRepository(session)
        self._graph_service = EntityGraphService(session)

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
        Execute the hybrid read pipeline with Ebbinghaus decay & Knowledge Graph expansion.
        """
        start_time = time.perf_counter()

        # 1. Embed Query
        query_vector = await self._embedding.get_embedding(query)

        # 2. Qdrant Search
        fetch_limit = min(limit * 3, 100)
        raw_results = await self._vector_repo.search(
            query_vector=query_vector,
            tenant_id=tenant_id,
            external_user_id=external_user_id,
            memory_type=memory_type,
            limit=fetch_limit,
            score_threshold=score_threshold,
        )

        # 3. Extract query entity keywords for Knowledge Graph expansion
        triples = self._graph_service._extract_heuristic_triples(query)
        query_entities = set()
        for s, _, o in triples:
            query_entities.add(s)
            query_entities.add(o)

        # Fallback: extract capitalized terms
        if not query_entities:
            for word in query.split():
                clean_w = word.strip(",.?!").title()
                if len(clean_w) > 3 and clean_w.lower() not in ["what", "where", "when", "how", "with", "from"]:
                    query_entities.add(clean_w)

        kg_data: dict[str, Any] | None = None
        if query_entities:
            kg_data = await self._graph_repo.get_subgraph_for_entities(
                tenant_id=tenant_id,
                external_user_id=external_user_id,
                entity_names=list(query_entities),
            )

        if not raw_results:
            return MemorySearchResponse(
                results=[],
                query_time_ms=(time.perf_counter() - start_time) * 1000,
                knowledge_graph=kg_data,
            )

        # 4. Hydrate top candidate IDs from PostgreSQL to obtain full records & access counts
        ep_ids = [uuid.UUID(p.id) for p in raw_results if p.payload and p.payload.get("memory_type") == "episodic"]
        sem_ids = [uuid.UUID(p.id) for p in raw_results if p.payload and p.payload.get("memory_type") == "semantic"]

        ep_memories = await self._episodic_repo.get_by_ids(tenant_id, ep_ids)
        sem_memories = await self._semantic_repo.get_by_ids(tenant_id, sem_ids)

        db_memories: dict[uuid.UUID, Any] = {m.id: m for m in ep_memories}
        for sm in sem_memories:
            if sm.superseded_by is None:
                db_memories[sm.id] = sm

        now_ts = datetime.now(UTC).timestamp()

        # 5. Ebbinghaus Retrievability & Reciprocal Rank Fusion (RRF)
        scored_candidates: list[dict[str, Any]] = []
        for rank_idx, point in enumerate(raw_results):
            point_uuid = uuid.UUID(point.id)  # type: ignore
            db_record = db_memories.get(point_uuid)
            if not db_record:
                continue

            sim_score = point.score
            imp_score = getattr(db_record, "importance_score", 0.5)
            access_count = getattr(db_record, "access_count", 0)
            created_at = getattr(db_record, "created_at", datetime.now(UTC))

            # Calculate age in days
            age_days = max(0.01, (now_ts - created_at.timestamp()) / 86400.0)

            # Ebbinghaus Retrievability: R = exp(-age_days / (S * (1 + access_count)))
            retrievability = math.exp(-age_days / max(30.0 * (1 + access_count), 1.0))

            # Reciprocal Rank Fusion (RRF) composite formula:
            # RRF = 1 / (60 + dense_rank) + 0.4 * retrievability + 0.3 * imp_score
            rrf_score = (1.0 / (60 + rank_idx + 1)) + (0.4 * retrievability) + (0.3 * imp_score)

            scored_candidates.append(
                {
                    "record": db_record,
                    "type": point.payload.get("memory_type") if point.payload else "unknown",
                    "sim": sim_score,
                    "imp": imp_score,
                    "comp": round(rrf_score, 4),
                }
            )

        # Sort by composite score descending
        scored_candidates.sort(key=lambda x: x["comp"], reverse=True)
        top_k = scored_candidates[:limit]

        # 6. Format Output & Increment Access Count
        final_results = []
        for cand in top_k:
            rec = cand["record"]
            final_results.append(
                ScoredMemoryResult(
                    id=rec.id,
                    memory_type=cand["type"],
                    content=rec.content,
                    meta_data=rec.meta_data or {},
                    importance_score=cand["imp"],
                    similarity_score=cand["sim"],
                    composite_score=cand["comp"],
                    created_at=rec.created_at,
                )
            )

            # Increment access counts
            if cand["type"] == "episodic":
                await self._episodic_repo.increment_access_count(rec.id)
            else:
                await self._semantic_repo.increment_access_count(rec.id)

        query_time = (time.perf_counter() - start_time) * 1000.0
        logger.info(
            "memory_search_completed",
            tenant_id=str(tenant_id),
            results=len(final_results),
            time_ms=query_time,
        )

        return MemorySearchResponse(
            results=final_results,
            query_time_ms=query_time,
            knowledge_graph=kg_data,
        )
