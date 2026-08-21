"""
AtlasOS PostgreSQL Memory Repositories.

Data access classes for EpisodicMemory, SemanticMemory, and ContradictionLog.
Handles database-level operations matching the schemas defined in Phase 1.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select, update

from app.models.memory import ContradictionLog, EpisodicMemory, SemanticMemory
from app.repositories.base import BaseRepository

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


class EpisodicMemoryRepository(BaseRepository[EpisodicMemory]):
    """Repository for Episodic Memories."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=EpisodicMemory, session=session)  # type: ignore

    async def get_by_ids(
        self,
        tenant_id: uuid.UUID,
        ids: list[uuid.UUID],
    ) -> list[EpisodicMemory]:
        """Fetch multiple episodic memories by ID."""
        if not ids:
            return []

        stmt = select(EpisodicMemory).where(
            EpisodicMemory.tenant_id == tenant_id,
            EpisodicMemory.id.in_(ids),
        )
        result = await self.session.execute(stmt)  # type: ignore
        return list(result.scalars().all())

    async def increment_access_count(self, memory_id: uuid.UUID) -> None:
        """Atomically increment the access count."""
        stmt = (
            update(EpisodicMemory)
            .where(EpisodicMemory.id == memory_id)
            .values(access_count=EpisodicMemory.access_count + 1)
        )
        await self.session.execute(stmt)  # type: ignore


class SemanticMemoryRepository(BaseRepository[SemanticMemory]):
    """Repository for Semantic Memories."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=SemanticMemory, session=session)  # type: ignore

    async def get_by_ids(
        self,
        tenant_id: uuid.UUID,
        ids: list[uuid.UUID],
    ) -> list[SemanticMemory]:
        """Fetch multiple semantic memories by ID."""
        if not ids:
            return []

        stmt = select(SemanticMemory).where(
            SemanticMemory.tenant_id == tenant_id,
            SemanticMemory.id.in_(ids),
        )
        result = await self.session.execute(stmt)  # type: ignore
        return list(result.scalars().all())

    async def increment_access_count(self, memory_id: uuid.UUID) -> None:
        """Atomically increment the access count."""
        stmt = (
            update(SemanticMemory)
            .where(SemanticMemory.id == memory_id)
            .values(access_count=SemanticMemory.access_count + 1)
        )
        await self.session.execute(stmt)  # type: ignore

    async def mark_superseded(
        self,
        memory_id: uuid.UUID,
        superseded_by_id: uuid.UUID,
    ) -> None:
        """
        Mark a semantic fact as superseded by a newer fact.
        This effectively "soft deletes" it from active searches while
        retaining it for audit trails and temporal reasoning.
        """
        stmt = (
            update(SemanticMemory)
            .where(SemanticMemory.id == memory_id)
            .values(superseded_by=superseded_by_id)
        )
        await self.session.execute(stmt)  # type: ignore


class ContradictionLogRepository(BaseRepository[ContradictionLog]):
    """Repository for the Contradiction Log."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=ContradictionLog, session=session)  # type: ignore

    async def log_contradiction(
        self,
        tenant_id: uuid.UUID,
        new_fact_id: uuid.UUID,
        existing_fact_id: uuid.UUID,
        resolution_strategy: str,
        winning_fact_id: uuid.UUID | None = None,
        confidence_score: float | None = None,
    ) -> ContradictionLog:
        """Create a new contradiction log entry."""
        log_entry = ContradictionLog(
            tenant_id=tenant_id,
            new_fact_id=new_fact_id,
            existing_fact_id=existing_fact_id,
            resolution_strategy=resolution_strategy,
            winning_fact_id=winning_fact_id,
            confidence_score=confidence_score,
        )
        self.session.add(log_entry)  # type: ignore
        await self.session.flush()  # type: ignore
        return log_entry
