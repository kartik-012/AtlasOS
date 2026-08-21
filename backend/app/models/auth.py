"""
AtlasOS Authentication & Authorization Models.

Contains five related models that handle identity, access, and team management:

  1. TenantMembership: Maps users to tenants with roles (RBAC).
  2. OAuthAccount: Links external identity providers to user accounts.
  3. Session: Server-side session tracking for the developer console.
  4. ApiKey: Programmatic API credentials for SDK/agent access.
  5. TeamInvite: Pending invitations for new team members.

Design decisions:
  - RBAC via roles: Simplified to three levels (admin, member, read_only).
    Fine-grained permission scoping is handled at the API key level, not
    the membership level. This keeps the model simple while still allowing
    precise control for programmatic access.
  - OAuth account linking: A user can have multiple OAuth accounts from
    different providers (Google, GitHub, etc.), all linking to the same
    User record. This enables seamless sign-in from any linked provider.
  - Server-side sessions: Stateful sessions stored in PostgreSQL (cached
    in Redis) enable remote sign-out and audit trail. Stateless JWTs alone
    cannot be revoked without additional infrastructure.
  - API key hashing: Keys are bcrypt-hashed. The plaintext is shown once
    at creation and never stored or logged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass

    from app.models.tenant import Tenant
    from app.models.user import User


class TenantMembership(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """
    Maps a user to a tenant with a specific role.

    The unique constraint on (tenant_id, user_id) prevents duplicate
    memberships. The role column implements basic RBAC:
      - admin: Full access including team and settings management.
      - member: Standard access to memory and evaluation features.
      - read_only: View-only access for auditors and stakeholders.
    """

    __tablename__ = "tenant_memberships"

    __table_args__ = (
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_membership_tenant_user"),
        sa.CheckConstraint(
            "role IN ('admin', 'member', 'read_only')",
            name="valid_role",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="The user who is a member of the tenant.",
    )
    role: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        server_default="member",
        doc="The user's role within this tenant.",
    )
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="The user who invited this member. NULL if the founding admin.",
    )
    joined_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        doc="When the user accepted the invitation and joined.",
    )

    # --- Relationships ---
    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        back_populates="memberships",
    )
    user: Mapped[User] = relationship(
        "User",
        back_populates="memberships",
        foreign_keys=[user_id],
    )
    inviter: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[invited_by],
    )

    def __repr__(self) -> str:
        return (
            f"<TenantMembership(tenant_id={self.tenant_id}, "
            f"user_id={self.user_id}, role='{self.role}')>"
        )


class OAuthAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Links an external OAuth2 identity provider to a user account.

    Supports account linking: a single User can have OAuthAccounts from
    multiple providers (Google + GitHub, etc.). The unique constraint on
    (provider, provider_account_id) prevents duplicate provider links.

    Token fields (access_token_enc, refresh_token_enc) are encrypted at
    the application layer before storage. The database stores ciphertext only.

    The provider list is designed to be extensible:
      - Current: google, github
      - Future: microsoft (Entra ID), okta, auth0, SAML
    Adding new providers requires only a CHECK constraint update.
    """

    __tablename__ = "oauth_accounts"

    __table_args__ = (
        sa.UniqueConstraint(
            "provider",
            "provider_account_id",
            name="uq_oauth_provider_account",
        ),
        sa.CheckConstraint(
            "provider IN ('google', 'github', 'microsoft', 'okta')",
            name="valid_provider",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="The user this OAuth account is linked to.",
    )
    provider: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        doc="OAuth provider name (google, github, microsoft, okta).",
    )
    provider_account_id: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        doc="The user's unique ID from the OAuth provider.",
    )
    provider_email: Mapped[str | None] = mapped_column(
        sa.String(255),
        nullable=True,
        doc="Email from the OAuth provider. May differ from User.email.",
    )
    access_token_enc: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
        doc="Encrypted OAuth access token. Application-layer encryption.",
    )
    refresh_token_enc: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
        doc="Encrypted OAuth refresh token. Application-layer encryption.",
    )
    token_expires_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        doc="When the current access token expires.",
    )

    # --- Relationships ---
    user: Mapped[User] = relationship(
        "User",
        back_populates="oauth_accounts",
    )

    def __repr__(self) -> str:
        return f"<OAuthAccount(provider='{self.provider}', user_id={self.user_id})>"


class Session(UUIDPrimaryKeyMixin, TenantScopedMixin, Base):
    """
    Server-side session for the developer console.

    Tracks active user sessions to enable:
      - Remote sign-out (revoke sessions from the security settings page).
      - Session activity auditing (IP, user agent, last activity).
      - Concurrent session limits per user.

    Sessions are NOT updated after creation — they are created and optionally
    revoked. This is why there is no updated_at column (no TimestampMixin).
    The revoked_at timestamp is set when a session is invalidated.

    token_hash stores a SHA-256 hash of the session token. The plaintext
    token is stored only in the client-side cookie.
    """

    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="The user this session belongs to.",
    )
    token_hash: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        unique=True,
        doc="SHA-256 hash of the session token.",
    )
    ip_address: Mapped[str | None] = mapped_column(
        sa.String(45),
        nullable=True,
        doc="Client IP address. Supports IPv4 and IPv6.",
    )
    user_agent: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
        doc="Client User-Agent header for device identification.",
    )
    expires_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        doc="When this session expires and becomes invalid.",
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        doc="When this session was explicitly revoked. NULL if still active.",
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        doc="When the session was created.",
    )

    # --- Relationships ---
    user: Mapped[User] = relationship(
        "User",
        back_populates="sessions",
    )
    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        back_populates="sessions",
    )

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, user_id={self.user_id})>"


class ApiKey(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """
    Programmatic API key for SDK/agent access.

    API keys provide machine-to-machine authentication. They are scoped
    to a tenant and carry explicit permission arrays.

    Security model:
      - key_prefix: First 8 characters of the plaintext key, stored for
        identification (e.g., "atlas_k_"). Enables users to identify which
        key is which without exposing the full key.
      - key_hash: Bcrypt hash of the full key. The plaintext key is shown
        exactly once at creation time and never stored.
      - permissions: Array of permission scopes. Enables fine-grained
        access control beyond the membership role.

    Permission scopes:
      - memory:read — Query and retrieve memories.
      - memory:write — Create and update memories.
      - memory:admin — Delete memories, manage contradictions.
      - eval:run — Trigger evaluation runs.
    """

    __tablename__ = "api_keys"

    name: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        doc="Human-readable name for the API key (e.g., 'Production Backend').",
    )
    key_prefix: Mapped[str] = mapped_column(
        sa.String(8),
        nullable=False,
        index=True,
        doc="First 8 characters of the key for identification.",
    )
    key_hash: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        doc="Bcrypt hash of the full API key.",
    )
    permissions: Mapped[list[str]] = mapped_column(
        ARRAY(sa.String(50)),
        nullable=False,
        server_default=sa.text("ARRAY['memory:read']::varchar[]"),
        doc="Array of permission scopes granted to this key.",
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("true"),
        doc="Whether the key is active. Revoked keys set this to false.",
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of the last API call using this key.",
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        doc="Optional expiration date. NULL means the key never expires.",
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="The user who created this key.",
    )

    # --- Relationships ---
    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        back_populates="api_keys",
    )
    creator: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[created_by],
    )

    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, name='{self.name}', prefix='{self.key_prefix}')>"


class TeamInvite(UUIDPrimaryKeyMixin, TenantScopedMixin, Base):
    """
    Pending invitation for a new team member to join a tenant.

    Invitations are valid for 7 days (enforced at the application layer).
    Once accepted, a TenantMembership record is created and the invite
    status is updated to 'accepted'.

    The token_hash stores a SHA-256 hash of the invitation token sent
    via email. This prevents token theft from database dumps.

    Status lifecycle: pending → accepted | expired | revoked
    """

    __tablename__ = "team_invites"

    __table_args__ = (
        sa.CheckConstraint(
            "role IN ('admin', 'member', 'read_only')",
            name="valid_invite_role",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'expired', 'revoked')",
            name="valid_invite_status",
        ),
    )

    email: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        doc="Email address the invitation was sent to.",
    )
    role: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        server_default="member",
        doc="The role assigned to the invitee upon acceptance.",
    )
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="The user who sent the invitation.",
    )
    token_hash: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        unique=True,
        doc="SHA-256 hash of the invitation token.",
    )
    status: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        server_default="pending",
        doc="Current status of the invitation.",
    )
    expires_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        doc="When the invitation expires (typically created_at + 7 days).",
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        doc="When the invitation was accepted. NULL if not yet accepted.",
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        doc="When the invitation was created.",
    )

    # --- Relationships ---
    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        back_populates="team_invites",
    )
    inviter: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[invited_by],
    )

    def __repr__(self) -> str:
        return f"<TeamInvite(id={self.id}, email='{self.email}', status='{self.status}')>"
