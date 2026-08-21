from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import (
    TenantContext,
    get_db_session_with_tenant,
    get_tenant_context,
    require_role,
)
from app.core.logging import get_logger
from app.schemas.contradiction import (
    ContradictionListResponse,
    ContradictionResolveRequest,
    ContradictionResponse,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)
router = APIRouter(prefix="/contradictions", tags=["Contradictions"])


@router.get(
    "/",
    response_model=ContradictionListResponse,
    dependencies=[Depends(require_role("admin", "member", "read_only"))],
)
async def list_contradictions(
    status_filter: str | None = Query(None, alias="status", description="Optional status filter"),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session_with_tenant),
) -> Any:
    """List contradictions with optional status filter."""


@router.get(
    "/{contradiction_id}",
    response_model=ContradictionResponse,
    dependencies=[Depends(require_role("admin", "member", "read_only"))],
)
async def get_contradiction(
    contradiction_id: str,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session_with_tenant),
) -> Any:
    """Get single contradiction detail."""


@router.post(
    "/{contradiction_id}/resolve",
    response_model=ContradictionResponse,
    dependencies=[Depends(require_role("admin", "member"))],
)
async def resolve_contradiction(
    contradiction_id: str,
    resolve_in: ContradictionResolveRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session_with_tenant),
) -> Any:
    """Resolve a contradiction."""
