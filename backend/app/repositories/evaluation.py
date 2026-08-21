from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

from app.models.evaluation import EvaluationMetric, EvaluationRun
from app.repositories.base import BaseRepository

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


class EvaluationRunRepository(BaseRepository[EvaluationRun]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=EvaluationRun, session=session)  # type: ignore

    async def get_by_tenant(
        self, tenant_id: uuid.UUID, offset: int = 0, limit: int = 50
    ) -> list[EvaluationRun]:
        stmt = (
            select(EvaluationRun)
            .where(EvaluationRun.tenant_id == tenant_id)
            .offset(offset)
            .limit(limit)
            .order_by(EvaluationRun.created_at.desc())
        )

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(EvaluationRun)
            .where(EvaluationRun.tenant_id == tenant_id)
        )

        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create_run(
        self, tenant_id: uuid.UUID, run_type: str, triggered_by: uuid.UUID, config: dict[str, Any]
    ) -> EvaluationRun:
        run = EvaluationRun(
            tenant_id=tenant_id,
            run_type=run_type,
            status="pending",
            triggered_by=triggered_by,
            config=config,
        )
        return await self.create(run)


class EvaluationMetricRepository(BaseRepository[EvaluationMetric]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=EvaluationMetric, session=session)  # type: ignore

    async def get_by_run_id(self, run_id: uuid.UUID) -> list[EvaluationMetric]:
        stmt = (
            select(EvaluationMetric)
            .where(EvaluationMetric.evaluation_run_id == run_id)
            .order_by(EvaluationMetric.created_at.desc())
        )

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create_metric(
        self,
        run_id: uuid.UUID,
        metric_name: str,
        metric_value: float,
        target_value: float,
        passed: bool,
        details: dict[str, Any],
    ) -> EvaluationMetric:
        metric = EvaluationMetric(
            evaluation_run_id=run_id,
            metric_name=metric_name,
            metric_value=metric_value,
            target_value=target_value,
            passed=passed,
            details=details,
        )
        return await self.create(metric)
