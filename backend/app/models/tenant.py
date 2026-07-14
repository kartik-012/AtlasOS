"""
AtlasOS Tenant Model.

Represents a customer workspace in the multi-tenant architecture.
Each tenant is an isolated unit with its own:
  - Memory storage (episodic + semantic)
  - API keys and team members
  - Configuration (embedding provider, resolution policy, retention)
  - Billing plan limits

Tenant isolation is enforced at three levels:
  1. Application layer: tenant_id derived from auth context, never from request params.
  2. Database layer: Row-Level Security (RLS) policies on all tenant-scoped tables.
  3. Vector store layer: Qdrant queries always filter on tenant_id payload field.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.auth import ApiKey, Session, TeamInvite, TenantMembership
    from app.models.evaluation import EvaluationRun
    from app.models.memory import (
        CompressionLog,
        ContradictionLog,
        EpisodicMemory,
        SemanticMemory,
    )
    from app.models.notification import Notification
    from app.models.webhook import Webhook


class Tenant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Customer workspace. The root entity for multi-tenant isolation.

    Every tenant-scoped resource (memories, keys, evaluations, etc.)
    references this table via a foreign key with ON DELETE CASCADE.
    """

    __tablename__ = "tenants"

    __table_args__ = (
        sa.CheckConstraint(
            "plan IN ('free', 'pro', 'enterprise')",
            name="valid_plan",
        ),
        sa.CheckConstraint(
            "embedding_provider IN ('bge-large', 'openai', 'gemini', 'voyageai', 'jina', 'custom')",
            name="valid_embedding_provider",
        ),
        sa.CheckConstraint(
            "resolution_policy IN ('most_recent_wins', 'confidence_weighted', 'manual_review')",
            name="valid_resolution_policy",
        ),
        sa.CheckConstraint(
            "retention_days > 0",
            name="positive_retention_days",
        ),
        sa.CheckConstraint(
            "max_memories_per_user > 0",
            name="positive_max_memories",
        ),
        sa.CheckConstraint(
            "embedding_dimension > 0",
            name="positive_embedding_dimension",
        ),
    )

    # --- Core Identity ---
    name: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        doc="Human-readable tenant name.",
    )
    slug: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        unique=True,
        index=True,
        doc="URL-safe unique identifier. Used in API paths and console URLs.",
    )

    # --- Billing ---
    plan: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        server_default="free",
        doc="Billing plan tier. Determines feature access and limits.",
    )

    # --- Embedding Configuration ---
    embedding_provider: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        server_default="bge-large",
        doc="Selected embedding provider. Determines which service generates vectors.",
    )
    embedding_model: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        server_default="BAAI/bge-large-en-v1.5",
        doc="Specific model identifier within the selected provider.",
    )
    embedding_dimension: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("1024"),
        doc="Vector dimension. Must match the selected model's output dimension.",
    )

    # --- Memory Configuration ---
    resolution_policy: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        server_default="most_recent_wins",
        doc="Policy for resolving contradictions between semantic memories.",
    )
    retention_days: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("90"),
        doc="Number of days to retain episodic memories before cleanup.",
    )
    max_memories_per_user: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("10000"),
        doc="Maximum episodic + semantic memories per external_user_id.",
    )

    # --- Status ---
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("true"),
        doc="Whether the tenant is active. Inactive tenants cannot make API calls.",
    )

    # --- Relationships ---
    memberships: Mapped[list[TenantMembership]] = relationship(
        "TenantMembership",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    api_keys: Mapped[list[ApiKey]] = relationship(
        "ApiKey",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    sessions: Mapped[list[Session]] = relationship(
        "Session",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    team_invites: Mapped[list[TeamInvite]] = relationship(
        "TeamInvite",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    episodic_memories: Mapped[list[EpisodicMemory]] = relationship(
        "EpisodicMemory",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    semantic_memories: Mapped[list[SemanticMemory]] = relationship(
        "SemanticMemory",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    contradiction_logs: Mapped[list[ContradictionLog]] = relationship(
        "ContradictionLog",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    compression_logs: Mapped[list[CompressionLog]] = relationship(
        "CompressionLog",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    evaluation_runs: Mapped[list[EvaluationRun]] = relationship(
        "EvaluationRun",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    notifications: Mapped[list[Notification]] = relationship(
        "Notification",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    webhooks: Mapped[list[Webhook]] = relationship(
        "Webhook",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, slug='{self.slug}', plan='{self.plan}')>"
