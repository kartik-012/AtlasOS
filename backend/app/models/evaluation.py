"""
AtlasOS Evaluation Models.

Tracks quality evaluation runs and their measured metrics.

  1. EvaluationRun: Represents a single evaluation execution (manual,
     scheduled, or CI-triggered) that measures memory system quality.

  2. EvaluationMetric: Individual metric measurements within a run.

Evaluation metrics measured:
  - recall_at_k: Proportion of relevant memories retrieved in top-K results.
  - precision_at_k: Proportion of retrieved memories that are relevant.
  - contradiction_catch_rate: How many true contradictions the NLI detects.
  - false_positive_rate: How many non-contradictions are flagged incorrectly.
  - compression_fidelity: How well compressed facts preserve source information.
  - p95_latency_ms: 95th percentile end-to-end retrieval latency.

Each metric is compared against a target_value and marked as passed/failed.
This enables automated quality gates in CI pipelines.
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


class EvaluationRun(UUIDPrimaryKeyMixin, TenantScopedMixin, Base):
    """
    A single evaluation execution measuring memory system quality.

    Evaluation runs can be triggered by:
      - Manual: Developer clicks "Run Evaluation" in the console.
      - Scheduled: Celery beat triggers periodic evaluations.
      - CI: Triggered via API from a CI/CD pipeline.

    Status lifecycle: pending → running → completed | failed
    No updated_at — status tracked via started_at, completed_at, status.
    """

    __tablename__ = "evaluation_runs"

    __table_args__ = (
        sa.CheckConstraint(
            "run_type IN ('scheduled', 'manual', 'ci')",
            name="valid_run_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="valid_eval_status",
        ),
    )

    run_type: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        doc="How this evaluation was triggered.",
    )
    status: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        server_default="pending",
        doc="Current execution status.",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        doc="When the evaluation started executing.",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        doc="When the evaluation finished.",
    )
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="The user who triggered this evaluation (NULL for scheduled runs).",
    )
    config: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Configuration parameters for this evaluation run.",
    )
    error_message: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
        doc="Error message if the evaluation failed.",
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        doc="When the evaluation was created/enqueued.",
    )

    # --- Relationships ---
    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        back_populates="evaluation_runs",
    )
    triggerer: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[triggered_by],
    )
    metrics: Mapped[list[EvaluationMetric]] = relationship(
        "EvaluationMetric",
        back_populates="evaluation_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<EvaluationRun(id={self.id}, run_type='{self.run_type}', status='{self.status}')>"


class EvaluationMetric(UUIDPrimaryKeyMixin, Base):
    """
    A single metric measurement within an evaluation run.

    Each metric compares a measured value against a target threshold
    and records whether the target was met (passed=True/False).

    Metrics are write-once per evaluation run — they are never updated.
    No updated_at column.
    """

    __tablename__ = "evaluation_metrics"

    __table_args__ = (
        sa.CheckConstraint(
            "metric_name IN ("
            "'recall_at_k', 'precision_at_k', 'contradiction_catch_rate', "
            "'false_positive_rate', 'compression_fidelity', 'p95_latency_ms'"
            ")",
            name="valid_metric_name",
        ),
    )

    evaluation_run_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="The evaluation run this metric belongs to.",
    )
    metric_name: Mapped[str] = mapped_column(
        sa.String(100),
        nullable=False,
        doc="Name of the metric being measured.",
    )
    metric_value: Mapped[float] = mapped_column(
        sa.Double,
        nullable=False,
        doc="The measured value of this metric.",
    )
    target_value: Mapped[float] = mapped_column(
        sa.Double,
        nullable=False,
        doc="The target threshold for this metric.",
    )
    passed: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        doc="Whether the measured value met the target.",
    )
    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Additional detail about this metric measurement.",
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        doc="When this metric was recorded.",
    )

    # --- Relationships ---
    evaluation_run: Mapped[EvaluationRun] = relationship(
        "EvaluationRun",
        back_populates="metrics",
    )

    def __repr__(self) -> str:
        return (
            f"<EvaluationMetric(metric='{self.metric_name}', "
            f"value={self.metric_value}, passed={self.passed})>"
        )
