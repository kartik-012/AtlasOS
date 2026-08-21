"""
AtlasOS Authentication Schemas.

Pydantic v2 schemas for all authentication-related request and response
payloads: login, registration, JWT tokens, API keys, and OAuth2 flows.

Design decisions:
  - Separate Request and Response schemas for every operation. Request
    schemas validate input; Response schemas control output serialization.
  - Password validation enforces minimum 8 characters. Additional complexity
    rules (uppercase, digits, special chars) can be added via field validators.
  - API key responses include the plaintext key ONLY in the creation response
    (ApiKeyCreateResponse). All other responses use ApiKeyResponse which
    omits the plaintext key entirely.
  - OAuth2 schemas define the URL redirect and callback flows.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime
import uuid

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import AtlasBaseSchema

if TYPE_CHECKING:
    pass

# =============================================================================
# Registration
# =============================================================================


class UserRegisterRequest(AtlasBaseSchema):
    """Schema for new user registration via email/password."""

    email: EmailStr = Field(
        ...,
        description="User's email address. Must be unique across the system.",
        examples=["developer@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password. Minimum 8 characters.",
        examples=["SecureP@ss123"],
    )
    display_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Display name shown in the console.",
        examples=["Jane Developer"],
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Enforce minimum password complexity."""
        if len(v) < 8:
            msg = "Password must be at least 8 characters long."
            raise ValueError(msg)
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not (has_upper and has_lower and has_digit):
            msg = (
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, and one digit."
            )
            raise ValueError(msg)
        return v


# =============================================================================
# Login
# =============================================================================


class LoginRequest(AtlasBaseSchema):
    """Schema for email/password login."""

    email: EmailStr = Field(
        ...,
        description="Registered email address.",
        examples=["developer@example.com"],
    )
    password: str = Field(
        ...,
        description="Account password.",
        examples=["SecureP@ss123"],
    )


class TokenResponse(AtlasBaseSchema):
    """JWT token pair returned after successful authentication."""

    access_token: str = Field(
        ...,
        description="Short-lived JWT access token.",
    )
    refresh_token: str = Field(
        ...,
        description="Long-lived JWT refresh token.",
    )
    token_type: str = Field(
        default="bearer",
        description="Token type. Always 'bearer'.",
    )
    expires_in: int = Field(
        ...,
        description="Access token expiry time in seconds.",
    )


class TokenRefreshRequest(AtlasBaseSchema):
    """Request to exchange a refresh token for a new access token."""

    refresh_token: str = Field(
        ...,
        description="A valid refresh token.",
    )


class TenantSwitchRequest(AtlasBaseSchema):
    """Request to switch the active tenant context for the current session."""

    tenant_id: uuid.UUID = Field(
        ...,
        description="UUID of the tenant to switch to.",
    )


# =============================================================================
# API Keys
# =============================================================================


class ApiKeyCreateRequest(AtlasBaseSchema):
    """Schema for creating a new API key."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable name for the key.",
        examples=["Production Backend"],
    )
    permissions: list[str] = Field(
        default=["memory:read"],
        description="Permission scopes for this key.",
        examples=[["memory:read", "memory:write"]],
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Optional expiration datetime. NULL = never expires.",
    )

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, v: list[str]) -> list[str]:
        """Ensure all permissions are from the allowed set."""
        allowed = {"memory:read", "memory:write", "memory:admin", "eval:run"}
        invalid = set(v) - allowed
        if invalid:
            msg = f"Invalid permissions: {invalid}. Allowed: {sorted(allowed)}"
            raise ValueError(msg)
        if not v:
            msg = "At least one permission is required."
            raise ValueError(msg)
        return v


class ApiKeyCreateResponse(AtlasBaseSchema):
    """
    Response after creating an API key.

    Contains the plaintext key. This is the ONLY time the key is returned.
    """

    id: uuid.UUID
    name: str
    key_prefix: str
    plaintext_key: str = Field(
        ...,
        description="The full API key. Store it securely — it will NOT be shown again.",
    )
    permissions: list[str]
    is_active: bool
    expires_at: datetime | None
    created_at: datetime


class ApiKeyResponse(AtlasBaseSchema):
    """API key response without the plaintext key."""

    id: uuid.UUID
    name: str
    key_prefix: str
    permissions: list[str]
    is_active: bool
    last_used_at: datetime | None
    expires_at: datetime | None
    created_at: datetime


class ApiKeyRevokeRequest(AtlasBaseSchema):
    """Request to revoke an API key."""

    key_id: uuid.UUID = Field(
        ...,
        description="UUID of the API key to revoke.",
    )


# =============================================================================
# OAuth2
# =============================================================================


class OAuthLoginResponse(AtlasBaseSchema):
    """Response containing the OAuth2 authorization URL to redirect to."""

    authorization_url: str = Field(
        ...,
        description="URL to redirect the user's browser to for OAuth login.",
    )


class OAuthCallbackRequest(AtlasBaseSchema):
    """Schema for the OAuth2 callback with the authorization code."""

    code: str = Field(
        ...,
        description="Authorization code from the OAuth provider.",
    )
    state: str | None = Field(
        default=None,
        description="CSRF state parameter for verification.",
    )


# =============================================================================
# Password Management
# =============================================================================


class PasswordChangeRequest(AtlasBaseSchema):
    """Schema for changing the current user's password."""

    current_password: str = Field(
        ...,
        description="The user's current password.",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password. Minimum 8 characters.",
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, v: str) -> str:
        """Enforce minimum password complexity on new password."""
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not (has_upper and has_lower and has_digit):
            msg = (
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, and one digit."
            )
            raise ValueError(msg)
        return v
