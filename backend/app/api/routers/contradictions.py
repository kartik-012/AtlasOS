from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    TenantContext,
    get_tenant_context,
    get_db_session_with_tenant,
    require_role,
)
from app.core.logging import get_logger
from app.schemas.contradiction import (
    ContradictionResponse,
    ContradictionResolveRequest,
    ContradictionListResponse,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/contradictions", tags=["Contradictions"])


@router.get("/", response_model=ContradictionListResponse, dependencies=[Depends(require_role("admin", "member", "read_only"))])
async def list_contradictions(
    status_filter: Optional[str] = Query(None, alias="status", description="Optional status filter"),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session_with_tenant),
) -> Any:
    """List contradictions with optional status filter."""
    pass


@router.get("/{contradiction_id}", response_model=ContradictionResponse, dependencies=[Depends(require_role("admin", "member", "read_only"))])
async def get_contradiction(
    contradiction_id: str,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session_with_tenant),
) -> Any:
    """Get single contradiction detail."""
    pass


@router.post("/{contradiction_id}/resolve", response_model=ContradictionResponse, dependencies=[Depends(require_role("admin", "member"))])
async def resolve_contradiction(
    contradiction_id: str,
    resolve_in: ContradictionResolveRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session_with_tenant),
) -> Any:
    """Resolve a contradiction."""
    pass
