"""
AtlasOS Team Invite Schemas.

Pydantic v2 schemas for creating, listing, and accepting team invitations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime
import uuid

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import AtlasBaseSchema

if TYPE_CHECKING:
    pass


class InviteCreateRequest(AtlasBaseSchema):
    """Schema for inviting a new member to a tenant."""

    email: EmailStr = Field(
        ...,
        description="Email address of the person to invite.",
        examples=["newmember@example.com"],
    )
    role: str = Field(
        default="member",
        description="Role to assign to the invitee upon acceptance.",
        examples=["member"],
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Ensure the role is valid."""
        allowed = {"admin", "member", "read_only"}
        if v not in allowed:
            msg = f"Invalid role '{v}'. Must be one of: {sorted(allowed)}"
            raise ValueError(msg)
        return v


class InviteResponse(AtlasBaseSchema):
    """Team invitation data returned in API responses."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    role: str
    status: str
    invited_by: uuid.UUID | None
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime


class InviteAcceptRequest(AtlasBaseSchema):
    """Schema for accepting a team invitation via token."""

    token: str = Field(
        ...,
        description="The invitation token received via email.",
    )


class MemberRoleUpdateRequest(AtlasBaseSchema):
    """Schema for updating a team member's role."""

    role: str = Field(
        ...,
        description="New role for the member.",
        examples=["admin"],
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Ensure the role is valid."""
        allowed = {"admin", "member", "read_only"}
        if v not in allowed:
            msg = f"Invalid role '{v}'. Must be one of: {sorted(allowed)}"
            raise ValueError(msg)
        return v
