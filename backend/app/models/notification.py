"""
AtlasOS Notification Model.

In-app notifications delivered to console users via the notification
drawer. Notifications are created by background workers and API handlers
when significant events occur.

Notification types:
  - contradiction_detected: NLI pipeline found conflicting facts.
  - eval_completed: An evaluation run finished successfully.
  - eval_failed: An evaluation run encountered errors.
  - compression_completed: Background compression job finished.
  - key_expiring: An API key is approaching its expiration date.
  - team_invite: A team invitation was received.
  - system: System-level announcements or warnings.

Notifications are scoped to both a tenant and a user, so a user only
sees notifications relevant to their current workspace.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from datetime import datetime
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantScopedMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass

    from app.models.tenant import Tenant
    from app.models.user import User


class Notification(UUIDPrimaryKeyMixin, TenantScopedMixin, Base):
    """
    In-app notification for console users.

    Read/unread state is tracked via is_read and read_at. Notifications
    are never updated beyond marking them as read — the original content
    is immutable.

    No TimestampMixin: Notifications don't have updated_at since they
    are only marked as read (tracked separately via read_at).
    """

    __tablename__ = "notifications"

    __table_args__ = (
        sa.CheckConstraint(
            "type IN ("
            "'contradiction_detected', 'eval_completed', 'eval_failed', "
            "'compression_completed', 'key_expiring', 'team_invite', 'system'"
            ")",
            name="valid_notification_type",
        ),
        sa.Index(
            "ix_notifications_tenant_user_read",
            "tenant_id",
            "user_id",
            "is_read",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="The user this notification is for.",
    )
    type: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        doc="Notification type categorizing the event.",
    )
    title: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        doc="Short notification title shown in the drawer.",
    )
    message: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        doc="Full notification message body.",
    )
    is_read: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("false"),
        doc="Whether the user has read this notification.",
    )
    action_url: Mapped[str | None] = mapped_column(
        sa.String(1024),
        nullable=True,
        doc="URL to navigate to when the notification is clicked.",
    )
    meta_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Additional context depending on type (e.g., entity_id, action_url).",
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        doc="When the notification was created.",
    )
    read_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        doc="When the user marked this notification as read.",
    )

    # --- Relationships ---
    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        back_populates="notifications",
    )
    user: Mapped[User] = relationship(
        "User",
        back_populates="notifications",
    )

    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, type='{self.type}', is_read={self.is_read})>"
