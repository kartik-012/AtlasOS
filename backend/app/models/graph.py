"""
AtlasOS Knowledge Graph Domain Models.

Contains models for the Entity Memory Mesh:
  1. EntityNode: Represents a named entity or concept (e.g. Person, Organization, Location, Preference).
  2. EntityRelation: Represents a directed relationship edge between two entities (e.g. User PREFERS DarkMode).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.tenant import Tenant


class EntityNode(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """
    Named Entity Node in the Knowledge Graph Mesh.
    """

    __tablename__ = "entity_nodes"

    __table_args__ = (
        sa.Index(
            "ix_entity_node_tenant_user_name",
            "tenant_id",
            "external_user_id",
            "name",
            unique=True,
        ),
        sa.Index(
            "ix_entity_node_tenant_type",
            "tenant_id",
            "entity_type",
        ),
    )

    external_user_id: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        doc="Identifier of the end-user owning this entity.",
    )
    name: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        doc="Normalized name of the entity (e.g. 'Google', 'Dark Mode').",
    )
    entity_type: Mapped[str] = mapped_column(
        sa.String(100),
        nullable=False,
        server_default="CONCEPT",
        doc="Type classification: PERSON, ORGANIZATION, CONCEPT, LOCATION, PREFERENCE.",
    )
    attributes: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Arbitrary key-value entity properties.",
    )

    # Relationships
    tenant: Mapped[Tenant] = relationship("Tenant")

    outgoing_relations: Mapped[list[EntityRelation]] = relationship(
        "EntityRelation",
        foreign_keys="EntityRelation.source_node_id",
        cascade="all, delete-orphan",
        back_populates="source_node",
    )
    incoming_relations: Mapped[list[EntityRelation]] = relationship(
        "EntityRelation",
        foreign_keys="EntityRelation.target_node_id",
        cascade="all, delete-orphan",
        back_populates="target_node",
    )

    def __repr__(self) -> str:
        return f"<EntityNode(id={self.id}, name='{self.name}', type='{self.entity_type}')>"


class EntityRelation(UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, Base):
    """
    Directed relationship edge between two EntityNodes in the Knowledge Graph Mesh.
    """

    __tablename__ = "entity_relations"

    __table_args__ = (
        sa.Index(
            "ix_relation_source_target",
            "source_node_id",
            "target_node_id",
        ),
        sa.Index(
            "ix_relation_tenant_type",
            "tenant_id",
            "relation_type",
        ),
    )

    source_node_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("entity_nodes.id", ondelete="CASCADE"),
        nullable=False,
        doc="Origin entity node.",
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("entity_nodes.id", ondelete="CASCADE"),
        nullable=False,
        doc="Destination entity node.",
    )
    relation_type: Mapped[str] = mapped_column(
        sa.String(100),
        nullable=False,
        doc="Relation predicate type (e.g. PREFERS, WORKS_FOR, LIVES_IN).",
    )
    weight: Mapped[float] = mapped_column(
        sa.Double,
        nullable=False,
        server_default=sa.text("1.0"),
        doc="Edge weight / strength of association.",
    )
    source_memory_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid,
        nullable=True,
        doc="ID of the memory from which this relation was derived.",
    )
    source_memory_type: Mapped[str | None] = mapped_column(
        sa.String(50),
        nullable=True,
        doc="Type of the source memory ('episodic' or 'semantic').",
    )

    # Relationships
    tenant: Mapped[Tenant] = relationship("Tenant")
    source_node: Mapped[EntityNode] = relationship(
        "EntityNode",
        foreign_keys=[source_node_id],
        back_populates="outgoing_relations",
    )
    target_node: Mapped[EntityNode] = relationship(
        "EntityNode",
        foreign_keys=[target_node_id],
        back_populates="incoming_relations",
    )

    def __repr__(self) -> str:
        return f"<EntityRelation(id={self.id}, type='{self.relation_type}', {self.source_node_id}->{self.target_node_id})>"
