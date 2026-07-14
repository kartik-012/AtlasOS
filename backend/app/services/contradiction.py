"""
AtlasOS Contradiction Service.

Orchestrates the contradiction detection pipeline using the NLI provider.
Evaluates new semantic facts against the top-K most similar existing facts
in Qdrant to detect logical conflicts before committing them to memory.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger
from app.models.memory import ContradictionLog, SemanticMemory
from app.models.tenant import Tenant
from app.providers.base import NLIProvider
from app.repositories.memory import ContradictionLogRepository, SemanticMemoryRepository
from app.repositories.vector import VectorRepository

logger = get_logger(__name__)


class ContradictionService:
    """
    Service for detecting and resolving semantic contradictions.
    """

    def __init__(
        self,
        nli_provider: NLIProvider,
        vector_repo: VectorRepository,
        semantic_repo: SemanticMemoryRepository,
        log_repo: ContradictionLogRepository,
    ) -> None:
        self._nli = nli_provider
        self._vector_repo = vector_repo
        self._semantic_repo = semantic_repo
        self._log_repo = log_repo

    async def check_for_contradiction(
        self,
        tenant: Tenant,
        external_user_id: str,
        new_fact_content: str,
        new_fact_vector: list[float],
        new_fact_id: uuid.UUID,
    ) -> tuple[bool, uuid.UUID | None]:
        """
        Check if a new fact contradicts any existing semantic memories.

        Pipeline:
        1. Query Qdrant for top-K similar *semantic* memories.
        2. Fetch full content of those memories from Postgres.
        3. Pass pairs to the NLI provider.
        4. If contradiction detected, apply tenant resolution policy.

        Returns:
            Tuple of (contradiction_detected, contradiction_log_id).
        """
        # Step 1: Find candidates
        candidates = await self._vector_repo.search(
            query_vector=new_fact_vector,
            tenant_id=tenant.id,
            external_user_id=external_user_id,
            memory_type="semantic",
            limit=5,
            score_threshold=0.7,
        )

        if not candidates:
            return False, None

        # Step 2: Fetch full text from PG
        candidate_ids = [uuid.UUID(p.id) for p in candidates]
        existing_memories = await self._semantic_repo.get_by_ids(tenant.id, candidate_ids)

        # Build a map for easy lookup
        memory_map = {m.id: m for m in existing_memories}

        # Step 3: Evaluate pairs with NLI Model
        for point in candidates:
            point_uuid = uuid.UUID(point.id)
            existing_fact = memory_map.get(point_uuid)

            if not existing_fact or existing_fact.superseded_by is not None:
                continue

            is_contradiction, confidence = await self._nli.check_contradiction(
                premise=existing_fact.content,
                hypothesis=new_fact_content,
            )

            if is_contradiction:
                logger.info(
                    "contradiction_detected",
                    tenant_id=str(tenant.id),
                    new_fact_id=str(new_fact_id),
                    existing_fact_id=str(existing_fact.id),
                    confidence=confidence,
                )

                # Step 4: Resolve based on policy
                log_entry = await self._resolve_contradiction(
                    tenant=tenant,
                    new_fact_id=new_fact_id,
                    new_fact_content=new_fact_content,
                    existing_fact=existing_fact,
                    confidence=confidence,
                )

                return True, log_entry.id

        return False, None

    async def _resolve_contradiction(
        self,
        tenant: Tenant,
        new_fact_id: uuid.UUID,
        new_fact_content: str,
        existing_fact: SemanticMemory,
        confidence: float,
    ) -> ContradictionLog:
        """
        Apply the tenant's resolution policy to handle the contradiction.

        Policies:
        - `most_recent_wins`: The new fact automatically supersedes the old.
        - `manual_review`: Both coexist until a human or agent resolves it.
        - `confidence_weighted`: Higher confidence wins.
        """
        policy = tenant.resolution_policy or "most_recent_wins"
        auto_resolved = False
        resolution = "pending"

        if policy == "most_recent_wins":
            # Soft delete the old fact
            await self._semantic_repo.mark_superseded(
                memory_id=existing_fact.id,
                superseded_by_id=new_fact_id,
            )
            resolution = "new_fact_kept"
            auto_resolved = True

        elif policy == "confidence_weighted":
            # Keep whichever fact has higher associated confidence
            # For simplicity: new fact wins if NLI confidence > existing confidence_score
            if confidence > existing_fact.confidence_score:
                await self._semantic_repo.mark_superseded(
                    memory_id=existing_fact.id,
                    superseded_by_id=new_fact_id,
                )
                resolution = "new_fact_kept"
            else:
                resolution = "existing_fact_kept"
            auto_resolved = True

        # If 'manual_review', resolution stays 'pending'.

        # Log the event using the actual ContradictionLog model
        now = datetime.now(timezone.utc) if auto_resolved else None
        log_entry = ContradictionLog(
            tenant_id=tenant.id,
            new_fact_id=new_fact_id,
            existing_fact_id=existing_fact.id,
            new_fact_content=new_fact_content,
            existing_fact_content=existing_fact.content,
            contradiction_score=confidence,
            resolution=resolution,
            auto_resolved=auto_resolved,
            resolution_policy_applied=policy if auto_resolved else None,
            resolved_at=now,
        )
        self._log_repo.session.add(log_entry)
        await self._log_repo.session.flush()

        return log_entry
