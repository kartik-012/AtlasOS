"""initial_schema

Revision ID: 001
Revises:
Create Date: 2026-07-14 11:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ==============================================================================
    # 1. Custom Types and Functions
    # ==============================================================================

    # Enable Row-Level Security (RLS) on the database by creating the
    # updated_at trigger function that updates the timestamp column
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Function to prevent modification of audit logs
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Audit log entries are immutable and cannot be modified or deleted.';
        END;
        $$ LANGUAGE plpgsql;
    """)

    # ==============================================================================
    # 2. Table Creation
    # ==============================================================================

    # Tenants
    op.create_table(
        "tenants",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("plan", sa.String(length=50), server_default="free", nullable=False),
        sa.Column(
            "embedding_provider", sa.String(length=50), server_default="bge-large", nullable=False
        ),
        sa.Column(
            "embedding_model",
            sa.String(length=255),
            server_default="BAAI/bge-large-en-v1.5",
            nullable=False,
        ),
        sa.Column(
            "embedding_dimension", sa.Integer(), server_default=sa.text("1024"), nullable=False
        ),
        sa.Column(
            "resolution_policy",
            sa.String(length=50),
            server_default="most_recent_wins",
            nullable=False,
        ),
        sa.Column("retention_days", sa.Integer(), server_default=sa.text("90"), nullable=False),
        sa.Column(
            "max_memories_per_user", sa.Integer(), server_default=sa.text("10000"), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "embedding_provider IN ('bge-large', 'openai', 'gemini', 'voyageai', 'jina', 'custom')",
            name="valid_embedding_provider",
        ),
        sa.CheckConstraint("embedding_dimension > 0", name="positive_embedding_dimension"),
        sa.CheckConstraint("max_memories_per_user > 0", name="positive_max_memories"),
        sa.CheckConstraint("plan IN ('free', 'pro', 'enterprise')", name="valid_plan"),
        sa.CheckConstraint(
            "resolution_policy IN ('most_recent_wins', 'confidence_weighted', 'manual_review')",
            name="valid_resolution_policy",
        ),
        sa.CheckConstraint("retention_days > 0", name="positive_retention_days"),
        sa.PrimaryKeyConstraint("id", name="pk_tenants"),
    )
    op.create_index(op.f("ix_tenants_slug"), "tenants", ["slug"], unique=True)

    # Setup trigger for updated_at
    op.execute("""
        CREATE TRIGGER trg_tenants_updated_at
        BEFORE UPDATE ON tenants
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("avatar_url", sa.String(length=1024), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("email_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.execute("""
        CREATE TRIGGER trg_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    # Tenant Memberships
    op.create_table(
        "tenant_memberships",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=50), server_default="member", nullable=False),
        sa.Column("invited_by", sa.Uuid(), nullable=True),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("role IN ('admin', 'member', 'read_only')", name="valid_role"),
        sa.ForeignKeyConstraint(
            ["invited_by"],
            ["users.id"],
            name="fk_tenant_memberships_invited_by_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_tenant_memberships_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_tenant_memberships_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tenant_memberships"),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_membership_tenant_user"),
    )
    op.create_index(
        op.f("ix_tenant_memberships_tenant_id"), "tenant_memberships", ["tenant_id"], unique=False
    )
    op.create_index(
        op.f("ix_tenant_memberships_user_id"), "tenant_memberships", ["user_id"], unique=False
    )

    op.execute("""
        CREATE TRIGGER trg_tenant_memberships_updated_at
        BEFORE UPDATE ON tenant_memberships
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    # OAuth Accounts
    op.create_table(
        "oauth_accounts",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_account_id", sa.String(length=255), nullable=False),
        sa.Column("provider_email", sa.String(length=255), nullable=True),
        sa.Column("access_token_enc", sa.Text(), nullable=True),
        sa.Column("refresh_token_enc", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "provider IN ('google', 'github', 'microsoft', 'okta')", name="valid_provider"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_oauth_accounts_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_oauth_accounts"),
        sa.UniqueConstraint("provider", "provider_account_id", name="uq_oauth_provider_account"),
    )
    op.create_index(op.f("ix_oauth_accounts_user_id"), "oauth_accounts", ["user_id"], unique=False)

    op.execute("""
        CREATE TRIGGER trg_oauth_accounts_updated_at
        BEFORE UPDATE ON oauth_accounts
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    # Sessions
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_sessions_tenant_id_tenants", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_sessions_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sessions"),
        sa.UniqueConstraint("token_hash", name="uq_sessions_token_hash"),
    )
    op.create_index(op.f("ix_sessions_tenant_id"), "sessions", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_sessions_user_id"), "sessions", ["user_id"], unique=False)

    # API Keys
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("key_prefix", sa.String(length=8), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "permissions",
            postgresql.ARRAY(sa.String(length=50)),
            server_default=sa.text("ARRAY['memory:read']::varchar[]"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_api_keys_created_by_users", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_api_keys_tenant_id_tenants", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_api_keys"),
    )
    op.create_index(op.f("ix_api_keys_key_prefix"), "api_keys", ["key_prefix"], unique=False)
    op.create_index(op.f("ix_api_keys_tenant_id"), "api_keys", ["tenant_id"], unique=False)

    op.execute("""
        CREATE TRIGGER trg_api_keys_updated_at
        BEFORE UPDATE ON api_keys
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    # Team Invites
    op.create_table(
        "team_invites",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), server_default="member", nullable=False),
        sa.Column("invited_by", sa.Uuid(), nullable=True),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("role IN ('admin', 'member', 'read_only')", name="valid_invite_role"),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'expired', 'revoked')", name="valid_invite_status"
        ),
        sa.ForeignKeyConstraint(
            ["invited_by"],
            ["users.id"],
            name="fk_team_invites_invited_by_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_team_invites_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_team_invites"),
        sa.UniqueConstraint("token_hash", name="uq_team_invites_token_hash"),
    )
    op.create_index(op.f("ix_team_invites_tenant_id"), "team_invites", ["tenant_id"], unique=False)

    # Episodic Memories
    op.create_table(
        "episodic_memories",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("external_user_id", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding_model", sa.String(length=255), nullable=False),
        sa.Column("importance_score", sa.Double(), server_default=sa.text("0.5"), nullable=False),
        sa.Column("access_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("source", sa.String(length=50), server_default="api", nullable=False),
        sa.Column("session_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("meta_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("vector_id", sa.Uuid(), nullable=False),
        sa.Column("superseded", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("superseded_by", sa.Uuid(), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("access_count >= 0", name="non_negative_access_count"),
        sa.CheckConstraint(
            "importance_score >= 0.0 AND importance_score <= 1.0", name="valid_importance_score"
        ),
        sa.CheckConstraint("source IN ('api', 'sdk', 'console')", name="valid_source"),
        sa.ForeignKeyConstraint(
            ["superseded_by"],
            ["episodic_memories.id"],
            name="fk_episodic_memories_superseded_by_episodic_memories",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_episodic_memories_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_episodic_memories"),
        sa.UniqueConstraint("vector_id", name="uq_episodic_memories_vector_id"),
    )
    op.create_index(
        "ix_episodic_tenant_created",
        "episodic_memories",
        ["tenant_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_episodic_tenant_importance",
        "episodic_memories",
        ["tenant_id", "importance_score"],
        unique=False,
    )
    op.create_index(
        "ix_episodic_tenant_user",
        "episodic_memories",
        ["tenant_id", "external_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_episodic_memories_tenant_id"), "episodic_memories", ["tenant_id"], unique=False
    )

    op.execute("""
        CREATE TRIGGER trg_episodic_memories_updated_at
        BEFORE UPDATE ON episodic_memories
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    # Semantic Memories
    op.create_table(
        "semantic_memories",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("external_user_id", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding_model", sa.String(length=255), nullable=False),
        sa.Column("importance_score", sa.Double(), server_default=sa.text("0.5"), nullable=False),
        sa.Column("confidence_score", sa.Double(), server_default=sa.text("0.5"), nullable=False),
        sa.Column("source_episodic_id", sa.Uuid(), nullable=True),
        sa.Column("access_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("meta_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("vector_id", sa.Uuid(), nullable=False),
        sa.Column("superseded", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("superseded_by", sa.Uuid(), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("access_count >= 0", name="non_negative_sem_access_count"),
        sa.CheckConstraint(
            "confidence_score >= 0.0 AND confidence_score <= 1.0", name="valid_confidence_score"
        ),
        sa.CheckConstraint(
            "importance_score >= 0.0 AND importance_score <= 1.0",
            name="valid_sem_importance_score",
        ),
        sa.ForeignKeyConstraint(
            ["source_episodic_id"],
            ["episodic_memories.id"],
            name="fk_semantic_memories_source_episodic_id_episodic_memories",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by"],
            ["semantic_memories.id"],
            name="fk_semantic_memories_superseded_by_semantic_memories",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_semantic_memories_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_semantic_memories"),
        sa.UniqueConstraint("vector_id", name="uq_semantic_memories_vector_id"),
    )
    op.create_index(
        "ix_semantic_tenant_importance",
        "semantic_memories",
        ["tenant_id", "importance_score"],
        unique=False,
    )
    op.create_index(
        "ix_semantic_tenant_user",
        "semantic_memories",
        ["tenant_id", "external_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_semantic_memories_tenant_id"), "semantic_memories", ["tenant_id"], unique=False
    )

    op.execute("""
        CREATE TRIGGER trg_semantic_memories_updated_at
        BEFORE UPDATE ON semantic_memories
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    # Contradiction Log
    op.create_table(
        "contradiction_log",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("new_fact_id", sa.Uuid(), nullable=False),
        sa.Column("existing_fact_id", sa.Uuid(), nullable=False),
        sa.Column("new_fact_content", sa.Text(), nullable=False),
        sa.Column("existing_fact_content", sa.Text(), nullable=False),
        sa.Column("contradiction_score", sa.Double(), nullable=False),
        sa.Column("resolution", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("resolved_by", sa.Uuid(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auto_resolved", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("resolution_policy_applied", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "contradiction_score >= 0.0 AND contradiction_score <= 1.0",
            name="valid_contradiction_score",
        ),
        sa.CheckConstraint(
            "resolution IN ('pending', 'new_fact_kept', 'existing_fact_kept', 'both_kept')",
            name="valid_resolution",
        ),
        sa.ForeignKeyConstraint(
            ["existing_fact_id"],
            ["semantic_memories.id"],
            name="fk_contradiction_log_existing_fact_id_semantic_memories",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["new_fact_id"],
            ["semantic_memories.id"],
            name="fk_contradiction_log_new_fact_id_semantic_memories",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by"],
            ["users.id"],
            name="fk_contradiction_log_resolved_by_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_contradiction_log_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_contradiction_log"),
    )
    op.create_index(
        op.f("ix_contradiction_log_tenant_id"), "contradiction_log", ["tenant_id"], unique=False
    )

    # Compression Log
    op.create_table(
        "compression_log",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("source_memory_ids", postgresql.ARRAY(sa.Uuid()), nullable=False),
        sa.Column("source_memory_type", sa.String(length=50), nullable=False),
        sa.Column("resulting_semantic_id", sa.Uuid(), nullable=True),
        sa.Column("original_content_hash", sa.String(length=64), nullable=False),
        sa.Column("compressed_content", sa.Text(), nullable=False),
        sa.Column("fidelity_score", sa.Double(), nullable=True),
        sa.Column("compression_ratio", sa.Double(), nullable=True),
        sa.Column("model_used", sa.String(length=255), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "fidelity_score IS NULL OR (fidelity_score >= 0.0 AND fidelity_score <= 1.0)",
            name="valid_fidelity_score",
        ),
        sa.CheckConstraint(
            "source_memory_type IN ('episodic', 'semantic')", name="valid_source_memory_type"
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="valid_compression_status",
        ),
        sa.ForeignKeyConstraint(
            ["resulting_semantic_id"],
            ["semantic_memories.id"],
            name="fk_compression_log_resulting_semantic_id_semantic_memories",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_compression_log_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_compression_log"),
    )
    op.create_index(
        op.f("ix_compression_log_tenant_id"), "compression_log", ["tenant_id"], unique=False
    )

    # Evaluation Runs
    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("run_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("triggered_by", sa.Uuid(), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("run_type IN ('scheduled', 'manual', 'ci')", name="valid_run_type"),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')", name="valid_eval_status"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_evaluation_runs_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["triggered_by"],
            ["users.id"],
            name="fk_evaluation_runs_triggered_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evaluation_runs"),
    )
    op.create_index(
        op.f("ix_evaluation_runs_tenant_id"), "evaluation_runs", ["tenant_id"], unique=False
    )

    # Evaluation Metrics
    op.create_table(
        "evaluation_metrics",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("evaluation_run_id", sa.Uuid(), nullable=False),
        sa.Column("metric_name", sa.String(length=100), nullable=False),
        sa.Column("metric_value", sa.Double(), nullable=False),
        sa.Column("target_value", sa.Double(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "metric_name IN ('recall_at_k', 'precision_at_k', 'contradiction_catch_rate', 'false_positive_rate', 'compression_fidelity', 'p95_latency_ms')",
            name="valid_metric_name",
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_run_id"],
            ["evaluation_runs.id"],
            name="fk_evaluation_metrics_evaluation_run_id_evaluation_runs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evaluation_metrics"),
    )
    op.create_index(
        op.f("ix_evaluation_metrics_evaluation_run_id"),
        "evaluation_metrics",
        ["evaluation_run_id"],
        unique=False,
    )

    # Audit Log
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("api_key_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("resource_type", sa.String(length=255), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("request_body", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("meta_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_audit_log_tenant_id_tenants",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_log"),
    )
    op.create_index(op.f("ix_audit_log_tenant_id"), "audit_log", ["tenant_id"], unique=False)

    op.execute("""
        CREATE TRIGGER trg_audit_log_immutable
        BEFORE UPDATE OR DELETE ON audit_log
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_log_modification();
    """)

    # Webhooks
    op.create_table(
        "webhooks",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("events", postgresql.ARRAY(sa.String(length=100)), nullable=False),
        sa.Column("secret_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("failure_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_webhooks_created_by_users", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_webhooks_tenant_id_tenants", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_webhooks"),
    )
    op.create_index(
        "ix_webhooks_tenant_active", "webhooks", ["tenant_id", "is_active"], unique=False
    )
    op.create_index(op.f("ix_webhooks_tenant_id"), "webhooks", ["tenant_id"], unique=False)

    op.execute("""
        CREATE TRIGGER trg_webhooks_updated_at
        BEFORE UPDATE ON webhooks
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    # Webhook Deliveries
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("webhook_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("attempt_number", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("attempt_number >= 1", name="positive_attempt_number"),
        sa.CheckConstraint(
            "status IN ('pending', 'delivered', 'failed', 'retrying')",
            name="valid_delivery_status",
        ),
        sa.ForeignKeyConstraint(
            ["webhook_id"],
            ["webhooks.id"],
            name="fk_webhook_deliveries_webhook_id_webhooks",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_webhook_deliveries"),
    )
    op.create_index(
        op.f("ix_webhook_deliveries_webhook_id"),
        "webhook_deliveries",
        ["webhook_id"],
        unique=False,
    )

    # Notifications
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("action_url", sa.String(length=1024), nullable=True),
        sa.Column("meta_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "type IN ('contradiction_detected', 'eval_completed', 'eval_failed', 'compression_completed', 'key_expiring', 'team_invite', 'system')",
            name="valid_notification_type",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_notifications_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_notifications_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
    )
    op.create_index(
        "ix_notifications_tenant_user_read",
        "notifications",
        ["tenant_id", "user_id", "is_read"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notifications_tenant_id"), "notifications", ["tenant_id"], unique=False
    )
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"], unique=False)

    # ==============================================================================
    # 3. Row-Level Security (RLS)
    # ==============================================================================

    tenant_tables = [
        "tenant_memberships",
        "sessions",
        "api_keys",
        "team_invites",
        "episodic_memories",
        "semantic_memories",
        "contradiction_log",
        "compression_log",
        "evaluation_runs",
        "audit_log",
        "webhooks",
        "notifications",
    ]

    for table in tenant_tables:
        # Enable RLS on the table
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")

        # Create policy that filters rows based on the session variable
        # `app.current_tenant_id`. If the variable is not set, access is denied.
        # This policy applies to all operations (SELECT, INSERT, UPDATE, DELETE).
        op.execute(f"""
            CREATE POLICY {table}_tenant_isolation_policy ON {table}
            AS PERMISSIVE
            FOR ALL
            TO public
            USING (
                tenant_id = current_setting('app.current_tenant_id', true)::uuid
            )
            WITH CHECK (
                tenant_id = current_setting('app.current_tenant_id', true)::uuid
            );
        """)

        # Force RLS for table owners (e.g., the superuser) in production
        # In this implementation, the `app_user` role is used by the app,
        # but we also force RLS on the table itself just in case.
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")


def downgrade() -> None:
    # Disable RLS policies
    tenant_tables = [
        "notifications",
        "webhook_deliveries",
        "webhooks",
        "audit_log",
        "evaluation_metrics",
        "evaluation_runs",
        "compression_log",
        "contradiction_log",
        "semantic_memories",
        "episodic_memories",
        "team_invites",
        "api_keys",
        "sessions",
        "oauth_accounts",
        "tenant_memberships",
        "users",
        "tenants",
    ]

    for table in tenant_tables:
        if (
            table not in {"oauth_accounts", "users", "tenants", "evaluation_metrics", "webhook_deliveries"}
        ):
            op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation_policy ON {table};")
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

    # Drop tables in reverse order of creation
    op.drop_table("notifications")
    op.drop_table("webhook_deliveries")
    op.drop_table("webhooks")
    op.drop_table("audit_log")
    op.drop_table("evaluation_metrics")
    op.drop_table("evaluation_runs")
    op.drop_table("compression_log")
    op.drop_table("contradiction_log")
    op.drop_table("semantic_memories")
    op.drop_table("episodic_memories")
    op.drop_table("team_invites")
    op.drop_table("api_keys")
    op.drop_table("sessions")
    op.drop_table("oauth_accounts")
    op.drop_table("tenant_memberships")
    op.drop_table("users")
    op.drop_table("tenants")

    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_log_modification();")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
