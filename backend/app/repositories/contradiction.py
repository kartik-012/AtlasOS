from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select, update

from app.models.memory import ContradictionLog
from app.repositories.base import BaseRepository

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


class ContradictionRepository(BaseRepository[ContradictionLog]):
    """Repository for managing contradictions."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=ContradictionLog, session=session)  # type: ignore

    async def get_pending(
        self, tenant_id: uuid.UUID, offset: int = 0, limit: int = 50
    ) -> list[ContradictionLog]:
        stmt = (
            select(ContradictionLog)
            .where(
                ContradictionLog.tenant_id == tenant_id, ContradictionLog.resolution == "pending"
            )
            .offset(offset)
            .limit(limit)
            .order_by(ContradictionLog.created_at.desc())
        )

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_tenant(
        self,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
        status_filter: str | None = None,
    ) -> list[ContradictionLog]:
        stmt = select(ContradictionLog).where(ContradictionLog.tenant_id == tenant_id)
        if status_filter:
            stmt = stmt.where(ContradictionLog.resolution == status_filter)

        stmt = stmt.offset(offset).limit(limit).order_by(ContradictionLog.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_tenant(self, tenant_id: uuid.UUID, status_filter: str | None = None) -> int:
        stmt = (
            select(func.count())
            .select_from(ContradictionLog)
            .where(ContradictionLog.tenant_id == tenant_id)
        )
        if status_filter:
            stmt = stmt.where(ContradictionLog.resolution == status_filter)

        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def resolve(
        self, contradiction_id: uuid.UUID, resolution: str, resolved_by: uuid.UUID
    ) -> ContradictionLog:
        stmt = (
            update(ContradictionLog)
            .where(ContradictionLog.id == contradiction_id)
            .values(resolution=resolution, resolved_by=resolved_by, resolved_at=func.now())
            .returning(ContradictionLog)
        )

        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.scalar_one()
