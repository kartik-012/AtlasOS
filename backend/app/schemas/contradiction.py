from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import AtlasBaseSchema

if TYPE_CHECKING:
    from uuid import UUID


class ContradictionResponse(AtlasBaseSchema):
    """Schema for contradiction response."""

    id: UUID
    tenant_id: UUID
    new_fact_id: UUID
    existing_fact_id: UUID
    new_fact_content: str
    existing_fact_content: str
    contradiction_score: float
    resolution: str
    resolved_by: UUID | None
    resolved_at: datetime | None
    auto_resolved: bool
    resolution_policy_applied: str | None
    created_at: datetime


class ContradictionResolveRequest(BaseModel):
    """Schema for resolving a contradiction."""

    resolution: Literal["new_fact_kept", "existing_fact_kept", "both_kept"] = Field(
        ..., description="The resolution outcome"
    )


class ContradictionListResponse(AtlasBaseSchema):
    """Schema for paginated contradiction list response."""

    items: list[ContradictionResponse]
    total: int
