from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    TenantContext,
    get_tenant_context,
    get_db_session_with_tenant,
    require_role,
)
from app.core.logging import get_logger
from app.schemas.webhook import (
    WebhookCreateRequest,
    WebhookUpdateRequest,
    WebhookResponse,
    WebhookDeliveryResponse,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/", response_model=WebhookResponse, dependencies=[Depends(require_role("admin"))], status_code=status.HTTP_201_CREATED)
async def create_webhook(
    webhook_in: WebhookCreateRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session_with_tenant),
) -> Any:
    """Create a new webhook."""
    pass


@router.get("/", response_model=list[WebhookResponse], dependencies=[Depends(require_role("admin", "member"))])
async def list_webhooks(
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session_with_tenant),
) -> Any:
    """List webhooks."""
    pass


@router.patch("/{webhook_id}", response_model=WebhookResponse, dependencies=[Depends(require_role("admin"))])
async def update_webhook(
    webhook_id: str,
    webhook_in: WebhookUpdateRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session_with_tenant),
) -> Any:
    """Update a webhook."""
    pass


@router.delete("/{webhook_id}", dependencies=[Depends(require_role("admin"))], status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: str,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session_with_tenant),
) -> Any:
    """Delete a webhook."""
    pass


@router.post("/{webhook_id}/test", response_model=WebhookDeliveryResponse, dependencies=[Depends(require_role("admin"))])
async def test_webhook_delivery(
    webhook_id: str,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session_with_tenant),
) -> Any:
    """Test webhook delivery."""
    pass


@router.get("/{webhook_id}/deliveries", response_model=list[WebhookDeliveryResponse], dependencies=[Depends(require_role("admin", "member"))])
async def list_webhook_deliveries(
    webhook_id: str,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session_with_tenant),
) -> Any:
    """List webhook deliveries."""
    pass
