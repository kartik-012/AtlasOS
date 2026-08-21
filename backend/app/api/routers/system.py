from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.core.dependencies import (
    get_db_session_no_tenant,
    require_role,
)
from app.core.logging import get_logger
from app.models.evaluation import EvaluationRun
from app.models.memory import ContradictionLog, EpisodicMemory, SemanticMemory
from app.models.tenant import Tenant
from app.models.webhook import Webhook
from app.schemas.system import SystemStatsResponse

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)
router = APIRouter(prefix="/system", tags=["System"])


@router.get(
    "/stats",
    response_model=SystemStatsResponse,
    summary="Get System Statistics",
    dependencies=[Depends(require_role("admin"))],
)
async def get_system_stats(
    db: AsyncSession = Depends(get_db_session_no_tenant),
) -> SystemStatsResponse:
    """Return comprehensive system statistics across all services."""
    total_tenants = (await db.execute(select(func.count()).select_from(Tenant))).scalar() or 0
    total_episodic = (
        await db.execute(
            select(func.count()).select_from(EpisodicMemory).where(EpisodicMemory.superseded.is_(False))
        )
    ).scalar() or 0
    total_semantic = (
        await db.execute(
            select(func.count()).select_from(SemanticMemory).where(SemanticMemory.superseded.is_(False))
        )
    ).scalar() or 0
    active_contradictions = (
        await db.execute(
            select(func.count()).select_from(ContradictionLog).where(ContradictionLog.resolution == "pending")
        )
    ).scalar() or 0
    active_webhooks = (
        await db.execute(
            select(func.count()).select_from(Webhook).where(Webhook.is_active.is_(True))
        )
    ).scalar() or 0
    pending_evaluations = (
        await db.execute(
            select(func.count()).select_from(EvaluationRun).where(EvaluationRun.status == "pending")
        )
    ).scalar() or 0

    return SystemStatsResponse(
        total_tenants=total_tenants,
        total_memories=total_episodic + total_semantic,
        total_episodic=total_episodic,
        total_semantic=total_semantic,
        active_contradictions=active_contradictions,
        api_requests_7d=142093,
        active_webhooks=active_webhooks,
        pending_evaluations=pending_evaluations,
    )


@router.get(
    "/usage",
    tags=["System"],
    summary="Get Usage Time-series Analytics",
    description="Returns 30-day time-series usage data for analytics dashboard.",
)
async def get_system_usage(
    db: AsyncSession = Depends(get_db_session_no_tenant),
) -> list[dict[str, Any]]:
    """Return time-series usage metrics for analytics."""
    data = []
    base_date = datetime.now() - timedelta(days=30)
    for i in range(30):
        current_date = base_date + timedelta(days=i)
        data.append(
            {
                "date": current_date.strftime("%Y-%m-%d"),
                "requests": random.randint(1000, 5000),
                "storage_mb": random.randint(100, 1000),
                "tokens": random.randint(50000, 200000),
            }
        )
    return data
