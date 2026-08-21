"""knowledge_graph_schema

Revision ID: 002
Revises: 001
Create Date: 2026-08-21 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Entity Nodes Table
    op.create_table(
        "entity_nodes",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("external_user_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("entity_type", sa.String(length=100), server_default="CONCEPT", nullable=False),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_entity_node_tenant_user_name",
        "entity_nodes",
        ["tenant_id", "external_user_id", "name"],
        unique=True,
    )
    op.create_index(
        "ix_entity_node_tenant_type",
        "entity_nodes",
        ["tenant_id", "entity_type"],
        unique=False,
    )

    # RLS & Triggers for entity_nodes
    op.execute("ALTER TABLE entity_nodes ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY tenant_isolation_entity_nodes ON entity_nodes
        FOR ALL
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
    """)
    op.execute("""
        CREATE TRIGGER update_entity_nodes_modtime
        BEFORE UPDATE ON entity_nodes
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    # Entity Relations Table
    op.create_table(
        "entity_relations",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("source_node_id", sa.Uuid(), nullable=False),
        sa.Column("target_node_id", sa.Uuid(), nullable=False),
        sa.Column("relation_type", sa.String(length=100), nullable=False),
        sa.Column("weight", sa.Double(), server_default=sa.text("1.0"), nullable=False),
        sa.Column("source_memory_id", sa.Uuid(), nullable=True),
        sa.Column("source_memory_type", sa.String(length=50), nullable=True),
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
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_node_id"], ["entity_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["entity_nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_relation_source_target",
        "entity_relations",
        ["source_node_id", "target_node_id"],
        unique=False,
    )
    op.create_index(
        "ix_relation_tenant_type",
        "entity_relations",
        ["tenant_id", "relation_type"],
        unique=False,
    )

    # RLS & Triggers for entity_relations
    op.execute("ALTER TABLE entity_relations ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY tenant_isolation_entity_relations ON entity_relations
        FOR ALL
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
    """)
    op.execute("""
        CREATE TRIGGER update_entity_relations_modtime
        BEFORE UPDATE ON entity_relations
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    op.drop_table("entity_relations")
    op.drop_table("entity_nodes")
