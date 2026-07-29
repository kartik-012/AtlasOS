from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import AtlasBaseSchema


class EvaluationMetricResponse(AtlasBaseSchema):
    """Schema for evaluation metric response."""
    id: UUID
    metric_name: str
    metric_value: float
    target_value: float | None
    passed: bool
    details: dict[str, Any] | None
    created_at: datetime


class EvaluationRunResponse(AtlasBaseSchema):
    """Schema for evaluation run response."""
    id: UUID
    tenant_id: UUID
    run_type: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    triggered_by: UUID | None
    config: dict[str, Any] | None
    error_message: str | None
    created_at: datetime
    metrics: list[EvaluationMetricResponse] = Field(default_factory=list)


class EvaluationTriggerRequest(BaseModel):
    """Schema for triggering an evaluation run."""
    config: dict[str, Any] | None = Field(default=None, description="Optional configuration for the run")


class EvaluationListResponse(AtlasBaseSchema):
    """Schema for paginated evaluation run list response."""
    items: list[EvaluationRunResponse]
    total: int
