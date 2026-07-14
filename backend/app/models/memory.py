"""
AtlasOS Memory Domain Models.

Contains four models representing the core memory hierarchy and its
operational logs:

  1. EpisodicMemory: Time-stamped agent experiences. Raw interactions stored
     with embeddings for semantic search. The foundational memory type.

  2. SemanticMemory: Consolidated facts derived from episodic memories via
     compression or direct writes. Higher-order knowledge representation.

  3. ContradictionLog: Records conflicts detected between semantic memories
     by the NLI (Natural Language Inference) pipeline.

  4. CompressionLog: Tracks background summarization jobs that compress
     older episodic memories into semantic facts.

Memory lifecycle:
  Agent writes → EpisodicMemory → (NLI check) → SemanticMemory
                                                     ↓
                                          Contradiction detected?
                                          → ContradictionLog entry
                                          → Resolution applied

  Background: CompressionLog tracks episodic → semantic compression runs.

Supersession:
  Both EpisodicMemory and SemanticMemory support a supersession model.
  When a memory is updated (e.g., contradiction resolved), the old memory
  is marked as superseded (superseded=True) and points to the new memory
  via superseded_by. The old memory is excluded from search but preserved
  for audit trail purposes.

Vector store integration:
  Each memory has a vector_id (UUID) that maps to a Qdrant point ID.
  This enables dual-write consistency: Postgres stores the content and
  metadata, Qdrant stores the embedding vector.
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


class EpisodicMemory(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """
    Time-stamped agent experience.

    Stores raw interactions between an AI agent and its end-user, along
    with the embedding vector ID for semantic search. Each episodic memory
    is scoped to a (tenant_id, external_user_id) pair.

    The importance_score (0.0-1.0) is initially set by the write pipeline
    and periodically recalibrated by background workers based on access
    frequency and recency.
    """

    __tablename__ = "episodic_memories"

    __table_args__ = (
        sa.CheckConstraint(
            "importance_score >= 0.0 AND importance_score <= 1.0",
            name="valid_importance_score",
        ),
        sa.CheckConstraint(
            "access_count >= 0",
            name="non_negative_access_count",
        ),
        sa.CheckConstraint(
            "source IN ('api', 'sdk', 'console')",
            name="valid_source",
        ),
        sa.Index(
            "ix_episodic_tenant_user",
            "tenant_id",
            "external_user_id",
        ),
        sa.Index(
            "ix_episodic_tenant_created",
            "tenant_id",
            "created_at",
        ),
        sa.Index(
            "ix_episodic_tenant_importance",
            "tenant_id",
            "importance_score",
        ),
    )

    external_user_id: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        doc="Identifier of the agent's end-user. Provided by the SDK caller.",
    )
    content: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        doc="The raw text content of the memory.",
    )
    embedding_model: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        doc="The model used to generate the embedding (e.g., 'BAAI/bge-large-en-v1.5').",
    )
    importance_score: Mapped[float] = mapped_column(
        sa.Double,
        nullable=False,
        server_default=sa.text("0.5"),
        doc="Importance score (0.0-1.0). Higher = more important for retrieval.",
    )
    access_count: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("0"),
        doc="Number of times this memory has been retrieved.",
    )
    source: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        server_default="api",
        doc="How this memory was created: api, sdk, or console.",
    )
    session_context: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Optional session context from the agent (task info, conversation metadata).",
    )
    metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Arbitrary key-value metadata attached by the caller.",
    )
    vector_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid,
        nullable=False,
        unique=True,
        doc="Qdrant point ID. Maps this memory to its embedding vector.",
    )

    # --- Supersession ---
    superseded: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("false"),
        doc="Whether this memory has been replaced by a newer version.",
    )
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("episodic_memories.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID of the memory that replaced this one.",
    )
    superseded_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        doc="When this memory was superseded.",
    )

    # --- Relationships ---
    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        back_populates="episodic_memories",
    )
    successor: Mapped[EpisodicMemory | None] = relationship(
        "EpisodicMemory",
        remote_side="EpisodicMemory.id",
        foreign_keys=[superseded_by],
    )

    def __repr__(self) -> str:
        return (
            f"<EpisodicMemory(id={self.id}, "
            f"external_user_id='{self.external_user_id}')>"
        )


class SemanticMemory(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """
    Consolidated fact derived from episodic memories.

    Semantic memories represent higher-order knowledge extracted from
    raw experiences. They are created via:
      1. Direct semantic writes through the API.
      2. Background compression of episodic memories.
      3. Contradiction resolution (creating a new fact from conflicting ones).

    The confidence_score (0.0-1.0) reflects how confident the system is
    in the accuracy of this fact. It is influenced by:
      - Number of supporting episodic memories.
      - Recency of supporting evidence.
      - Whether contradictions have been detected and resolved.
    """

    __tablename__ = "semantic_memories"

    __table_args__ = (
        sa.CheckConstraint(
            "importance_score >= 0.0 AND importance_score <= 1.0",
            name="valid_sem_importance_score",
        ),
        sa.CheckConstraint(
            "confidence_score >= 0.0 AND confidence_score <= 1.0",
            name="valid_confidence_score",
        ),
        sa.CheckConstraint(
            "access_count >= 0",
            name="non_negative_sem_access_count",
        ),
        sa.Index(
            "ix_semantic_tenant_user",
            "tenant_id",
            "external_user_id",
        ),
        sa.Index(
            "ix_semantic_tenant_importance",
            "tenant_id",
            "importance_score",
        ),
    )

    external_user_id: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        doc="Identifier of the agent's end-user.",
    )
    content: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        doc="The consolidated fact text.",
    )
    embedding_model: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        doc="The model used to generate the embedding.",
    )
    importance_score: Mapped[float] = mapped_column(
        sa.Double,
        nullable=False,
        server_default=sa.text("0.5"),
        doc="Importance score (0.0-1.0) for retrieval ranking.",
    )
    confidence_score: Mapped[float] = mapped_column(
        sa.Double,
        nullable=False,
        server_default=sa.text("0.5"),
        doc="Confidence score (0.0-1.0) reflecting accuracy certainty.",
    )
    source_episodic_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("episodic_memories.id", ondelete="SET NULL"),
        nullable=True,
        doc="The episodic memory this fact was extracted from (if applicable).",
    )
    access_count: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("0"),
        doc="Number of times this memory has been retrieved.",
    )
    metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Arbitrary key-value metadata attached by the caller.",
    )
    vector_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid,
        nullable=False,
        unique=True,
        doc="Qdrant point ID. Maps this fact to its embedding vector.",
    )

    # --- Supersession ---
    superseded: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("false"),
        doc="Whether this fact has been replaced by a newer version.",
    )
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("semantic_memories.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID of the fact that replaced this one.",
    )
    superseded_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        doc="When this fact was superseded.",
    )

    # --- Relationships ---
    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        back_populates="semantic_memories",
    )
    source_episodic: Mapped[EpisodicMemory | None] = relationship(
        "EpisodicMemory",
        foreign_keys=[source_episodic_id],
    )
    successor: Mapped[SemanticMemory | None] = relationship(
        "SemanticMemory",
        remote_side="SemanticMemory.id",
        foreign_keys=[superseded_by],
    )

    def __repr__(self) -> str:
        return (
            f"<SemanticMemory(id={self.id}, "
            f"external_user_id='{self.external_user_id}')>"
        )


class ContradictionLog(UUIDPrimaryKeyMixin, TenantScopedMixin, Base):
    """
    Records a detected contradiction between two semantic memories.

    When the NLI pipeline detects that a new semantic fact contradicts
    an existing fact (e.g., "User lives in Paris" vs "User lives in London"),
    it creates a ContradictionLog entry with:
      - References to both facts.
      - The contradiction confidence score from the NLI model.
      - The resolution outcome (once resolved).

    Resolution lifecycle: pending → (new_fact_kept | existing_fact_kept | both_kept)

    No updated_at: Contradictions are resolved once and never modified again.
    Resolution is tracked via resolved_at and resolution fields.
    """

    __tablename__ = "contradiction_log"

    __table_args__ = (
        sa.CheckConstraint(
            "contradiction_score >= 0.0 AND contradiction_score <= 1.0",
            name="valid_contradiction_score",
        ),
        sa.CheckConstraint(
            "resolution IN ('pending', 'new_fact_kept', 'existing_fact_kept', 'both_kept')",
            name="valid_resolution",
        ),
    )

    new_fact_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("semantic_memories.id", ondelete="CASCADE"),
        nullable=False,
        doc="The newly written semantic memory that triggered the conflict.",
    )
    existing_fact_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("semantic_memories.id", ondelete="CASCADE"),
        nullable=False,
        doc="The existing semantic memory that conflicts with the new fact.",
    )
    new_fact_content: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        doc="Snapshot of the new fact's content at detection time.",
    )
    existing_fact_content: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        doc="Snapshot of the existing fact's content at detection time.",
    )
    contradiction_score: Mapped[float] = mapped_column(
        sa.Double,
        nullable=False,
        doc="NLI model's confidence that the facts contradict (0.0-1.0).",
    )
    resolution: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        server_default="pending",
        doc="Outcome of the contradiction resolution.",
    )
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="The user who resolved the contradiction. NULL if auto-resolved.",
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        doc="When the contradiction was resolved.",
    )
    auto_resolved: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("false"),
        doc="Whether the contradiction was resolved automatically by policy.",
    )
    resolution_policy_applied: Mapped[str | None] = mapped_column(
        sa.String(50),
        nullable=True,
        doc="The tenant's resolution policy that was applied (if auto-resolved).",
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        doc="When the contradiction was detected.",
    )

    # --- Relationships ---
    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        back_populates="contradiction_logs",
    )
    new_fact: Mapped[SemanticMemory] = relationship(
        "SemanticMemory",
        foreign_keys=[new_fact_id],
    )
    existing_fact: Mapped[SemanticMemory] = relationship(
        "SemanticMemory",
        foreign_keys=[existing_fact_id],
    )
    resolver: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[resolved_by],
    )

    def __repr__(self) -> str:
        return (
            f"<ContradictionLog(id={self.id}, "
            f"resolution='{self.resolution}')>"
        )


class CompressionLog(UUIDPrimaryKeyMixin, TenantScopedMixin, Base):
    """
    Tracks a background compression job.

    Compression jobs summarize multiple episodic memories into a single
    semantic fact, reducing storage while preserving knowledge. Each log
    entry records:
      - Which memories were compressed (source_memory_ids array).
      - The resulting semantic fact (resulting_semantic_id).
      - Quality metrics (fidelity_score, compression_ratio).
      - Execution status and timing.

    Status lifecycle: pending → running → completed | failed

    No updated_at: Status progression is tracked via started_at,
    completed_at, and status. The record represents an immutable
    execution trace.
    """

    __tablename__ = "compression_log"

    __table_args__ = (
        sa.CheckConstraint(
            "fidelity_score IS NULL OR (fidelity_score >= 0.0 AND fidelity_score <= 1.0)",
            name="valid_fidelity_score",
        ),
        sa.CheckConstraint(
            "source_memory_type IN ('episodic', 'semantic')",
            name="valid_source_memory_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="valid_compression_status",
        ),
    )

    source_memory_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(sa.Uuid),
        nullable=False,
        doc="Array of memory IDs that were compressed.",
    )
    source_memory_type: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        doc="Type of source memories: 'episodic' or 'semantic'.",
    )
    resulting_semantic_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("semantic_memories.id", ondelete="SET NULL"),
        nullable=True,
        doc="The semantic memory produced by this compression. NULL if failed.",
    )
    original_content_hash: Mapped[str] = mapped_column(
        sa.String(64),
        nullable=False,
        doc="SHA-256 hash of concatenated source contents for deduplication.",
    )
    compressed_content: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        doc="The compressed/summarized text content.",
    )
    fidelity_score: Mapped[float | None] = mapped_column(
        sa.Double,
        nullable=True,
        doc="How faithfully the summary preserves source information (0.0-1.0).",
    )
    compression_ratio: Mapped[float | None] = mapped_column(
        sa.Double,
        nullable=True,
        doc="Ratio of compressed size to original size.",
    )
    model_used: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        doc="The LLM or model used for summarization.",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        doc="When the compression job started executing.",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        doc="When the compression job finished.",
    )
    status: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        server_default="pending",
        doc="Current execution status.",
    )
    error_message: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
        doc="Error message if the compression job failed.",
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        doc="When the compression job was created/enqueued.",
    )

    # --- Relationships ---
    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        back_populates="compression_logs",
    )
    resulting_semantic: Mapped[SemanticMemory | None] = relationship(
        "SemanticMemory",
        foreign_keys=[resulting_semantic_id],
    )

    def __repr__(self) -> str:
        return (
            f"<CompressionLog(id={self.id}, "
            f"status='{self.status}')>"
        )
