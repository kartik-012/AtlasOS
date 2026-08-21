"""
AtlasOS Tenant Schemas.

Pydantic v2 schemas for tenant creation, updates, and responses.
Tenant schemas enforce slug format validation and ensure configuration
values match the allowed options defined in the database CHECK constraints.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from datetime import datetime
import uuid

from pydantic import Field, field_validator

from app.schemas.common import AtlasBaseSchema

if TYPE_CHECKING:
    pass


class TenantCreateRequest(AtlasBaseSchema):
    """Schema for creating a new tenant workspace."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable tenant name.",
        examples=["My AI Project"],
    )
    slug: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="URL-safe unique identifier. Lowercase letters, numbers, hyphens only.",
        examples=["my-ai-project"],
    )

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Enforce URL-safe slug format."""
        if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", v) and len(v) > 1:
            msg = "Slug must contain only lowercase letters, numbers, and hyphens. Must start and end with a letter or number."
            raise ValueError(msg)
        if len(v) == 1 and not re.match(r"^[a-z0-9]$", v):
            msg = "Single-character slug must be a letter or number."
            raise ValueError(msg)
        return v


class TenantUpdateRequest(AtlasBaseSchema):
    """Schema for updating tenant settings. All fields are optional."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated tenant name.",
    )
    embedding_provider: str | None = Field(
        default=None,
        description="Embedding provider to use.",
    )
    embedding_model: str | None = Field(
        default=None,
        max_length=255,
        description="Specific model within the provider.",
    )
    embedding_dimension: int | None = Field(
        default=None,
        gt=0,
        description="Vector dimension. Must match the model output.",
    )
    resolution_policy: str | None = Field(
        default=None,
        description="Contradiction resolution policy.",
    )
    retention_days: int | None = Field(
        default=None,
        gt=0,
        description="Number of days to retain episodic memories.",
    )
    max_memories_per_user: int | None = Field(
        default=None,
        gt=0,
        description="Maximum memories per external_user_id.",
    )

    @field_validator("embedding_provider")
    @classmethod
    def validate_embedding_provider(cls, v: str | None) -> str | None:
        """Validate against allowed embedding providers."""
        if v is None:
            return v
        allowed = {"bge-large", "openai", "gemini", "voyageai", "jina", "custom"}
        if v not in allowed:
            msg = f"Invalid embedding_provider '{v}'. Must be one of: {sorted(allowed)}"
            raise ValueError(msg)
        return v

    @field_validator("resolution_policy")
    @classmethod
    def validate_resolution_policy(cls, v: str | None) -> str | None:
        """Validate against allowed resolution policies."""
        if v is None:
            return v
        allowed = {"most_recent_wins", "confidence_weighted", "manual_review"}
        if v not in allowed:
            msg = f"Invalid resolution_policy '{v}'. Must be one of: {sorted(allowed)}"
            raise ValueError(msg)
        return v


class TenantResponse(AtlasBaseSchema):
    """Tenant data returned in API responses."""

    id: uuid.UUID
    name: str
    slug: str
    plan: str
    embedding_provider: str
    embedding_model: str
    embedding_dimension: int
    resolution_policy: str
    retention_days: int
    max_memories_per_user: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TenantMemberResponse(AtlasBaseSchema):
    """Tenant membership data returned in API responses."""

    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    display_name: str
    role: str
    joined_at: datetime
