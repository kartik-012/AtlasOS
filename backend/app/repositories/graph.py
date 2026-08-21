"""
AtlasOS Entity Graph Repository.

Provides data access methods for managing Knowledge Graph nodes and relations.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.graph import EntityNode, EntityRelation
from app.repositories.base import BaseRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class EntityGraphRepository(BaseRepository[EntityNode]):
    """
    Repository for managing Knowledge Graph entity nodes and relationships.
    """

    model_class = EntityNode

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EntityNode)

    async def get_node_by_name(
        self,
        tenant_id: uuid.UUID,
        external_user_id: str,
        name: str,
    ) -> EntityNode | None:
        """
        Fetch entity node by tenant, user ID, and normalized name.
        """
        stmt = (
            select(EntityNode)
            .where(
                EntityNode.tenant_id == tenant_id,
                EntityNode.external_user_id == external_user_id,
                EntityNode.name == name,
            )
            .options(
                selectinload(EntityNode.outgoing_relations),
                selectinload(EntityNode.incoming_relations),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_node(
        self,
        tenant_id: uuid.UUID,
        external_user_id: str,
        name: str,
        entity_type: str = "CONCEPT",
        attributes: dict[str, Any] | None = None,
    ) -> EntityNode:
        """
        Fetch or create an EntityNode by name.
        """
        existing = await self.get_node_by_name(tenant_id, external_user_id, name)
        if existing:
            if attributes:
                merged = {**(existing.attributes or {}), **attributes}
                existing.attributes = merged
                await self._session.flush()
            return existing

        node = EntityNode(
            tenant_id=tenant_id,
            external_user_id=external_user_id,
            name=name,
            entity_type=entity_type,
            attributes=attributes or {},
        )
        self._session.add(node)
        await self._session.flush()
        return node

    async def add_relation(
        self,
        tenant_id: uuid.UUID,
        source_node_id: uuid.UUID,
        target_node_id: uuid.UUID,
        relation_type: str,
        weight: float = 1.0,
        source_memory_id: uuid.UUID | None = None,
        source_memory_type: str | None = None,
    ) -> EntityRelation:
        """
        Add or reinforce a directed relationship between two nodes.
        """
        stmt = select(EntityRelation).where(
            EntityRelation.tenant_id == tenant_id,
            EntityRelation.source_node_id == source_node_id,
            EntityRelation.target_node_id == target_node_id,
            EntityRelation.relation_type == relation_type,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.weight += 0.5
            await self._session.flush()
            return existing

        relation = EntityRelation(
            tenant_id=tenant_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            relation_type=relation_type,
            weight=weight,
            source_memory_id=source_memory_id,
            source_memory_type=source_memory_type,
        )
        self._session.add(relation)
        await self._session.flush()
        return relation

    async def get_subgraph_for_entities(
        self,
        tenant_id: uuid.UUID,
        external_user_id: str,
        entity_names: list[str],
    ) -> dict[str, Any]:
        """
        Retrieve sub-graph (nodes + edges) connected to a list of seed entity names.
        """
        stmt = (
            select(EntityNode)
            .where(
                EntityNode.tenant_id == tenant_id,
                EntityNode.external_user_id == external_user_id,
                EntityNode.name.in_(entity_names),
            )
            .options(
                selectinload(EntityNode.outgoing_relations).selectinload(EntityRelation.target_node),
                selectinload(EntityNode.incoming_relations).selectinload(EntityRelation.source_node),
            )
        )
        result = await self._session.execute(stmt)
        seed_nodes = list(result.scalars().all())

        nodes_dict: dict[uuid.UUID, dict[str, Any]] = {}
        edges_list: list[dict[str, Any]] = []

        for node in seed_nodes:
            nodes_dict[node.id] = {
                "id": str(node.id),
                "name": node.name,
                "type": node.entity_type,
                "attributes": node.attributes or {},
            }

            for rel in node.outgoing_relations:
                edges_list.append(
                    {
                        "id": str(rel.id),
                        "source": str(rel.source_node_id),
                        "target": str(rel.target_node_id),
                        "relation": rel.relation_type,
                        "weight": rel.weight,
                    }
                )
                if rel.target_node and rel.target_node.id not in nodes_dict:
                    nodes_dict[rel.target_node.id] = {
                        "id": str(rel.target_node.id),
                        "name": rel.target_node.name,
                        "type": rel.target_node.entity_type,
                        "attributes": rel.target_node.attributes or {},
                    }

            for rel in node.incoming_relations:
                edges_list.append(
                    {
                        "id": str(rel.id),
                        "source": str(rel.source_node_id),
                        "target": str(rel.target_node_id),
                        "relation": rel.relation_type,
                        "weight": rel.weight,
                    }
                )
                if rel.source_node and rel.source_node.id not in nodes_dict:
                    nodes_dict[rel.source_node.id] = {
                        "id": str(rel.source_node.id),
                        "name": rel.source_node.name,
                        "type": rel.source_node.entity_type,
                        "attributes": rel.source_node.attributes or {},
                    }

        return {
            "nodes": list(nodes_dict.values()),
            "edges": edges_list,
        }
