"""
AtlasOS Webhook Models.

Supports outbound event delivery to external services via HTTP webhooks.

  1. Webhook: Configuration for an outbound webhook endpoint.
  2. WebhookDelivery: Tracks individual delivery attempts for each event.

Webhook events are fire-and-forget with retries. The delivery system:
  - Attempts immediate delivery when an event occurs.
  - On failure, schedules exponential backoff retries (up to a max).
  - Tracks failure_count on the parent Webhook for circuit-breaking.
  - Records every delivery attempt in WebhookDelivery for debugging.

Security:
  - secret_hash: HMAC signing secret (hashed). Used to sign the webhook
    payload so the receiver can verify authenticity.
  - Response bodies are stored for debugging but may be truncated for
    large responses.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User


class Webhook(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """
    Outbound webhook endpoint configuration.

    Each webhook subscribes to specific event types and delivers
    JSON payloads to the configured URL when those events occur.
    """

    __tablename__ = "webhooks"

    __table_args__ = (
        sa.Index(
            "ix_webhooks_tenant_active",
            "tenant_id",
            "is_active",
        ),
    )

    url: Mapped[str] = mapped_column(
        sa.String(2048),
        nullable=False,
        doc="The HTTP(S) endpoint URL to deliver events to.",
    )
    events: Mapped[list[str]] = mapped_column(
        ARRAY(sa.String(100)),
        nullable=False,
        doc="Array of event types this webhook subscribes to.",
    )
    secret_hash: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        doc="Hashed HMAC signing secret for payload verification.",
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("true"),
        doc="Whether this webhook is active and should receive events.",
    )
    description: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
        doc="Human-readable description of what this webhook is for.",
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="The user who created this webhook.",
    )
    failure_count: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("0"),
        doc="Consecutive delivery failures. Used for circuit-breaking.",
    )
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        doc="When this webhook was last triggered.",
    )
    last_failure_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        doc="When the last delivery failure occurred.",
    )

    # --- Relationships ---
    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        back_populates="webhooks",
    )
    creator: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[created_by],
    )
    deliveries: Mapped[list[WebhookDelivery]] = relationship(
        "WebhookDelivery",
        back_populates="webhook",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Webhook(id={self.id}, url='{self.url}')>"


class WebhookDelivery(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Tracks an individual webhook delivery attempt.

    Each event dispatched to a webhook creates a delivery record.
    Failed deliveries may spawn retry records with incremented
    attempt_number.

    Status lifecycle: pending → delivered | failed | retrying
    """

    __tablename__ = "webhook_deliveries"

    __table_args__ = (
        sa.CheckConstraint(
            "status IN ('pending', 'delivered', 'failed', 'retrying')",
            name="valid_delivery_status",
        ),
        sa.CheckConstraint(
            "attempt_number >= 1",
            name="positive_attempt_number",
        ),
    )

    webhook_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("webhooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="The webhook this delivery belongs to.",
    )
    event_type: Mapped[str] = mapped_column(
        sa.String(100),
        nullable=False,
        doc="The type of event being delivered.",
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        doc="The JSON payload sent to the webhook endpoint.",
    )
    response_status: Mapped[int | None] = mapped_column(
        sa.Integer,
        nullable=True,
        doc="HTTP status code from the webhook endpoint response.",
    )
    response_body: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
        doc="Response body from the endpoint (may be truncated).",
    )
    attempt_number: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("1"),
        doc="Which attempt this is (1-based).",
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        doc="When the delivery was successfully completed.",
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        doc="When the next retry is scheduled (if status is 'retrying').",
    )
    status: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        server_default="pending",
        doc="Current delivery status.",
    )
    error_message: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
        doc="Error message if delivery failed.",
    )

    # --- Relationships ---
    webhook: Mapped[Webhook] = relationship(
        "Webhook",
        back_populates="deliveries",
    )

    def __repr__(self) -> str:
        return (
            f"<WebhookDelivery(id={self.id}, "
            f"event='{self.event_type}', status='{self.status}')>"
        )
