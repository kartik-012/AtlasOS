from __future__ import annotations

from typing import TYPE_CHECKING, Any
from datetime import datetime

from pydantic import Field

from app.schemas.common import AtlasBaseSchema

if TYPE_CHECKING:
    from uuid import UUID


class AuditLogResponse(AtlasBaseSchema):
    """Schema for audit log response."""

    id: UUID
    tenant_id: UUID
    user_id: UUID | None
    api_key_id: UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    ip_address: str | None
    request_body: dict[str, Any] | None
    response_status: int | None
    metadata_: dict[str, Any] | None = Field(None, alias="metadata")
    created_at: datetime


class AuditLogListResponse(AtlasBaseSchema):
    """Schema for paginated audit log list response."""

    items: list[AuditLogResponse]
    total: int
