from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, status

from app.core.dependencies import (
    TenantContext,
    get_db_session_with_tenant,
    get_tenant_context,
    require_role,
)
from app.core.logging import get_logger
from app.schemas.evaluation import (
    EvaluationListResponse,
    EvaluationRunResponse,
    EvaluationTriggerRequest,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)
router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


@router.post(
    "/trigger",
    response_model=EvaluationRunResponse,
    dependencies=[Depends(require_role("admin"))],
    status_code=status.HTTP_201_CREATED,
)
async def trigger_evaluation_run(
    trigger_in: EvaluationTriggerRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session_with_tenant),
) -> Any:
    """Trigger a new evaluation run."""


@router.get(
    "/",
    response_model=EvaluationListResponse,
    dependencies=[Depends(require_role("admin", "member", "read_only"))],
)
async def list_evaluation_runs(
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session_with_tenant),
) -> Any:
    """List evaluation runs."""


@router.get(
    "/{run_id}",
    response_model=EvaluationRunResponse,
    dependencies=[Depends(require_role("admin", "member", "read_only"))],
)
async def get_evaluation_run(
    run_id: str,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session_with_tenant),
) -> Any:
    """Get run detail with metrics."""
