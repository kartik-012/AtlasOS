"""
AtlasOS Audit Log Model.

Immutable, append-only security log for recording all significant operations
performed within a tenant's workspace.

CRITICAL SECURITY PROPERTIES:
  1. IMMUTABLE: The audit_log table has UPDATE and DELETE operations blocked
     at the database level via:
     - A trigger that raises an exception on UPDATE or DELETE attempts.
     - REVOKE UPDATE, DELETE on audit_log from the application role.
  2. No updated_at column: Since rows are never modified, tracking update
     timestamps is meaningless and would be misleading.
  3. ON DELETE RESTRICT on tenant_id: Audit logs are preserved even if
     someone attempts to delete a tenant. This prevents audit trail
     destruction.
  4. No FK on user_id and api_key_id: These are stored as plain UUIDs
     (not foreign keys) to preserve audit records even after the referenced
     user or API key is deleted.

The audit log records:
  - WHO performed the action (user_id or api_key_id)
  - WHAT action was performed (action + resource_type + resource_id)
  - WHEN it was performed (created_at)
  - WHERE from (ip_address + user_agent)
  - WHAT was sent (request_body — sanitized to remove secrets)
  - WHAT was the result (response_status)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from datetime import datetime
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class AuditLog(UUIDPrimaryKeyMixin, Base):
    """
    Immutable audit log entry.

    Records all significant operations for compliance and security
    forensics. This table intentionally does NOT use:
      - TimestampMixin (no updated_at, since rows are never updated)
      - TenantScopedMixin (uses a custom FK with ON DELETE RESTRICT)

    Immutability is enforced at the database level, not the application
    level, as defense-in-depth against application bugs or compromised
    application code.
    """

    __tablename__ = "audit_log"

    # Custom tenant FK with RESTRICT: prevent tenant deletion if audit logs exist.
    # This is a deliberate deviation from the CASCADE policy used on other tables.
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Tenant this audit event belongs to. RESTRICT prevents accidental deletion.",
    )

    # WHO — Stored as plain UUIDs (not FKs) to preserve records after user/key deletion.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid,
        nullable=True,
        doc="User who performed the action. NULL for API key operations.",
    )
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid,
        nullable=True,
        doc="API key used for the operation. NULL for console operations.",
    )

    # WHAT
    action: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        doc="Action performed (e.g., 'memory.create', 'api_key.revoke').",
    )
    resource_type: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        doc="Type of resource affected (e.g., 'episodic_memory', 'api_key').",
    )
    resource_id: Mapped[str | None] = mapped_column(
        sa.String(255),
        nullable=True,
        doc="ID of the affected resource. NULL for list/search operations.",
    )

    # WHERE
    ip_address: Mapped[str | None] = mapped_column(
        sa.String(45),
        nullable=True,
        doc="Client IP address. Supports IPv4 and IPv6.",
    )
    user_agent: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
        doc="Client User-Agent header.",
    )

    # REQUEST CONTEXT
    request_body: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Sanitized request body. MUST NOT contain passwords, tokens, or secrets.",
    )
    response_status: Mapped[int | None] = mapped_column(
        sa.Integer,
        nullable=True,
        doc="HTTP response status code.",
    )
    meta_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Additional structured context (e.g., changes made, error details).",
    )

    # WHEN
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        doc="When the event occurred. Immutable — never modified.",
    )

    # NOTE: No updated_at column. This table is immutable by design.
    # NOTE: No relationships defined. user_id and api_key_id are not FKs.

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, action='{self.action}', "
            f"resource_type='{self.resource_type}')>"
        )
