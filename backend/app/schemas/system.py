from __future__ import annotations

from app.schemas.common import AtlasBaseSchema


class SystemStatsResponse(AtlasBaseSchema):
    """Schema for system statistics response."""

    total_tenants: int
    total_memories: int
    total_episodic: int
    total_semantic: int
    active_contradictions: int
    api_requests_7d: int
    active_webhooks: int
    pending_evaluations: int
