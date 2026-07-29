from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import EvaluationRun
from app.repositories.evaluation import EvaluationRunRepository, EvaluationMetricRepository
from app.core.logging import get_logger

logger = get_logger(__name__)

class EvaluationService:
    """Service for managing evaluation runs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._run_repo = EvaluationRunRepository(session)
        self._metric_repo = EvaluationMetricRepository(session)

    async def trigger_evaluation(
        self, 
        tenant_id: uuid.UUID, 
        run_type: str, 
        triggered_by: uuid.UUID, 
        config: dict[str, Any]
    ) -> EvaluationRun:
        run = await self._run_repo.create_run(
            tenant_id=tenant_id,
            run_type=run_type,
            triggered_by=triggered_by,
            config=config
        )
        
        logger.info(f"Triggering evaluation {run.id} for tenant {tenant_id}")
        return run

    async def list_runs(self, tenant_id: uuid.UUID, offset: int = 0, limit: int = 50) -> tuple[list[EvaluationRun], int]:
        runs = await self._run_repo.get_by_tenant(tenant_id, offset, limit)
        total = await self._run_repo.count_by_tenant(tenant_id)
        return runs, total

    async def get_run_detail(self, run_id: uuid.UUID) -> tuple[EvaluationRun | None, list]:
        run = await self._run_repo.get_by_id(run_id)
        if not run:
            return None, []
            
        metrics = await self._metric_repo.get_by_run_id(run_id)
        return run, metrics
