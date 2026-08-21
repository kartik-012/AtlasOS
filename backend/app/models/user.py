"""
AtlasOS User Model.

Represents a console user account. Users are global entities — they exist
independently of tenants and can belong to multiple tenants via
tenant_memberships.

Authentication supports two methods (both can be used for the same account):
  1. Email + Password: password_hash stores bcrypt hash.
  2. OAuth2 SSO: Linked via oauth_accounts table.

password_hash is NULLABLE to support OAuth-only accounts (users who sign up
exclusively via Google/GitHub without setting a password).

Account linking: A user can sign in via email/password OR OAuth while using
the same account, enabling a seamless transition between auth methods.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass

    from app.models.auth import OAuthAccount, Session, TenantMembership
    from app.models.notification import Notification


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Console user account.

    Global entity — not scoped to any single tenant.
    Users join tenants via the tenant_memberships table.
    """

    __tablename__ = "users"

    # --- Identity ---
    email: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        unique=True,
        index=True,
        doc="Unique email address. Used as the primary login identifier.",
    )
    password_hash: Mapped[str | None] = mapped_column(
        sa.String(255),
        nullable=True,
        doc="Bcrypt password hash. NULL for OAuth-only accounts.",
    )
    display_name: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        doc="User's display name shown in the console UI.",
    )
    avatar_url: Mapped[str | None] = mapped_column(
        sa.String(1024),
        nullable=True,
        doc="URL to the user's avatar image. May come from OAuth provider.",
    )

    # --- Status ---
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("true"),
        doc="Whether the account is active. Deactivated users cannot log in.",
    )
    email_verified: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("false"),
        doc="Whether the user has verified their email address.",
    )

    # --- Activity ---
    last_login_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of the user's last successful login.",
    )

    # --- Relationships ---
    memberships: Mapped[list[TenantMembership]] = relationship(
        "TenantMembership",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="TenantMembership.user_id",
    )
    oauth_accounts: Mapped[list[OAuthAccount]] = relationship(
        "OAuthAccount",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    sessions: Mapped[list[Session]] = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    notifications: Mapped[list[Notification]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}')>"
