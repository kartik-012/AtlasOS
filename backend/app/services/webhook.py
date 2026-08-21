from __future__ import annotations

from typing import TYPE_CHECKING, Any

from passlib.hash import argon2

from app.core.logging import get_logger
from app.models.webhook import Webhook
from app.repositories.webhook import WebhookRepository

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class WebhookService:
    """Service for managing webhooks."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = WebhookRepository(session)

    async def create_webhook(
        self,
        tenant_id: uuid.UUID,
        url: str,
        events: list[str],
        secret: str,
        description: str,
        created_by: uuid.UUID,
    ) -> Webhook:
        secret_hash = argon2.hash(secret) if secret else None

        webhook = Webhook(
            tenant_id=tenant_id,
            url=url,
            events=events,
            secret_hash=secret_hash,
            description=description,
            created_by=created_by,
            is_active=True,
            failure_count=0,
        )

        logger.info(f"Creating webhook for tenant {tenant_id}")
        return await self._repo.create(webhook)

    async def list_webhooks(
        self, tenant_id: uuid.UUID, offset: int = 0, limit: int = 50
    ) -> tuple[list[Webhook], int]:
        webhooks = await self._repo.get_by_tenant(tenant_id, offset, limit)
        total = await self._repo.count_by_tenant(tenant_id)
        return webhooks, total

    async def update_webhook(self, webhook_id: uuid.UUID, update_data: dict[str, Any]) -> Webhook:
        webhook = await self._repo.get_by_id(webhook_id)
        if not webhook:
            raise ValueError(f"Webhook {webhook_id} not found")

        if "secret" in update_data:
            secret = update_data.pop("secret")
            if secret:
                update_data["secret_hash"] = argon2.hash(secret)

        return await self._repo.update(webhook, update_data)

    async def delete_webhook(self, webhook_id: uuid.UUID) -> None:
        webhook = await self._repo.get_by_id(webhook_id)
        if webhook:
            await self._repo.delete(webhook)

    async def test_webhook(self, webhook_id: uuid.UUID) -> dict[str, Any]:
        webhook = await self._repo.get_by_id(webhook_id)
        if not webhook:
            raise ValueError(f"Webhook {webhook_id} not found")

        # Mock test behavior
        logger.info(f"Testing webhook {webhook_id}")
        return {"status": "success", "message": "Webhook test triggered successfully"}
