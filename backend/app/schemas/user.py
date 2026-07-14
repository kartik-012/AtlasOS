"""
AtlasOS User Schemas.

Pydantic v2 schemas for user profile retrieval and updates.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.schemas.common import AtlasBaseSchema


class UserResponse(AtlasBaseSchema):
    """User profile data returned in API responses."""

    id: uuid.UUID
    email: EmailStr
    display_name: str
    avatar_url: str | None
    is_active: bool
    email_verified: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class UserUpdateRequest(AtlasBaseSchema):
    """Schema for updating user profile. All fields are optional."""

    display_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated display name.",
    )
    avatar_url: str | None = Field(
        default=None,
        max_length=1024,
        description="Updated avatar URL.",
    )


class UserWithTenantsResponse(AtlasBaseSchema):
    """User profile with their tenant memberships."""

    id: uuid.UUID
    email: EmailStr
    display_name: str
    avatar_url: str | None
    is_active: bool
    email_verified: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime
    tenants: list[UserTenantInfo]


class UserTenantInfo(AtlasBaseSchema):
    """Minimal tenant info as seen from the user's perspective."""

    tenant_id: uuid.UUID
    tenant_name: str
    tenant_slug: str
    role: str
    joined_at: datetime


# Rebuild UserWithTenantsResponse after UserTenantInfo is defined
UserWithTenantsResponse.model_rebuild()
