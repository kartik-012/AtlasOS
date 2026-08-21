from __future__ import annotations

from typing import TYPE_CHECKING, Any
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.common import AtlasBaseSchema

if TYPE_CHECKING:
    from uuid import UUID


class WebhookCreateRequest(BaseModel):
    """Schema for creating a new webhook."""

    url: HttpUrl = Field(..., description="The endpoint URL for the webhook")
    events: list[str] = Field(..., description="List of events to subscribe to")
    description: str | None = Field(
        default=None, description="Optional description of the webhook"
    )
    secret: str = Field(..., min_length=16, description="Secret used to sign the webhook payload")


class WebhookUpdateRequest(BaseModel):
    """Schema for updating an existing webhook."""

    url: HttpUrl | None = Field(default=None, description="The endpoint URL for the webhook")
    events: list[str] | None = Field(default=None, description="List of events to subscribe to")
    description: str | None = Field(
        default=None, description="Optional description of the webhook"
    )
    is_active: bool | None = Field(default=None, description="Whether the webhook is active")


class WebhookResponse(AtlasBaseSchema):
    """Schema for webhook response."""

    id: UUID
    url: HttpUrl
    events: list[str]
    is_active: bool
    description: str | None
    failure_count: int
    last_triggered_at: datetime | None
    created_at: datetime
    updated_at: datetime | None


class WebhookDeliveryResponse(AtlasBaseSchema):
    """Schema for webhook delivery response."""

    id: UUID
    webhook_id: UUID
    event_type: str
    payload: dict[str, Any]
    response_status: int | None
    attempt_number: int
    status: str
    delivered_at: datetime | None
    error_message: str | None
    created_at: datetime


class WebhookTestRequest(BaseModel):
    """Schema for requesting a webhook test."""

    webhook_id: UUID
