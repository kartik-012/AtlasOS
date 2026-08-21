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
from app.schemas.audit import AuditLogListResponse

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)
router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get(
    "/",
    response_model=AuditLogListResponse,
    dependencies=[Depends(require_role("admin", "member", "read_only"))],
)
async def list_audit_logs(
    action: str | None = Query(None, description="Filter by action"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    date_from: datetime | None = Query(None, description="Start date for filtering"),
    date_to: datetime | None = Query(None, description="End date for filtering"),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session_with_tenant),
) -> Any:
    """List audit log entries with optional filters."""
