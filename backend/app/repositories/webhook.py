from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import Webhook, WebhookDelivery
from app.repositories.base import BaseRepository

class WebhookRepository(BaseRepository[Webhook]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=Webhook, session=session)

    async def get_by_tenant(self, tenant_id: uuid.UUID, offset: int = 0, limit: int = 50) -> list[Webhook]:
        stmt = select(Webhook).where(
            Webhook.tenant_id == tenant_id
        ).offset(offset).limit(limit).order_by(Webhook.created_at.desc())
        
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Webhook).where(
            Webhook.tenant_id == tenant_id
        )
        
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_active_for_event(self, tenant_id: uuid.UUID, event_type: str) -> list[Webhook]:
        stmt = select(Webhook).where(
            Webhook.tenant_id == tenant_id,
            Webhook.is_active == True,
            Webhook.events.contains([event_type])
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def increment_failure_count(self, webhook_id: uuid.UUID) -> None:
        stmt = update(Webhook).where(
            Webhook.id == webhook_id
        ).values(
            failure_count=Webhook.failure_count + 1,
            last_failure_at=func.now()
        )
        await self._session.execute(stmt)
        await self._session.flush()

class WebhookDeliveryRepository(BaseRepository[WebhookDelivery]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=WebhookDelivery, session=session)

    async def get_by_webhook(self, webhook_id: uuid.UUID, offset: int = 0, limit: int = 50) -> list[WebhookDelivery]:
        stmt = select(WebhookDelivery).where(
            WebhookDelivery.webhook_id == webhook_id
        ).offset(offset).limit(limit).order_by(WebhookDelivery.delivered_at.desc())
        
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create_delivery(self, webhook_id: uuid.UUID, event_type: str, payload: dict[str, Any]) -> WebhookDelivery:
        delivery = WebhookDelivery(
            webhook_id=webhook_id,
            event_type=event_type,
            payload=payload,
            status="pending",
            attempt_number=0
        )
        return await self.create(delivery)
