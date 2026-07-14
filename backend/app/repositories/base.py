"""
AtlasOS Base Repository.

Provides a generic CRUD repository base class that all domain-specific
repositories inherit from. Encapsulates common patterns:
  - get_by_id: Fetch a single entity by primary key.
  - get_all: Paginated listing.
  - create: Insert a new entity.
  - update: Partial update of an existing entity.
  - delete: Remove an entity.

Design decisions:
  - Type-parameterized: Uses Generic[ModelT] so subclasses get full type
    inference without code duplication.
  - Session injection: The session is injected per-request by FastAPI DI.
    Repositories never create their own sessions.
  - No commit: Repositories do NOT call session.commit(). The session
    lifecycle (commit/rollback) is managed by the get_db_session dependency.
    This ensures all operations within a single request are atomic.
"""

from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Generic CRUD repository for SQLAlchemy models.

    Subclasses set `model_class` to bind operations to a specific table.
    """

    model_class: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the repository with a database session.

        Args:
            session: An async SQLAlchemy session, injected by FastAPI DI.
        """
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> ModelT | None:
        """
        Fetch a single entity by its primary key UUID.

        RLS automatically filters by tenant_id if the table is tenant-scoped
        and the session has a tenant context set.

        Args:
            entity_id: The UUID primary key.

        Returns:
            The entity instance, or None if not found.
        """
        stmt = select(self.model_class).where(self.model_class.id == entity_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 50,
    ) -> list[ModelT]:
        """
        Fetch a paginated list of entities.

        Args:
            offset: Number of rows to skip.
            limit: Maximum number of rows to return.

        Returns:
            A list of entity instances.
        """
        stmt = (
            select(self.model_class)
            .offset(offset)
            .limit(limit)
            .order_by(self.model_class.id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        """
        Count total entities (respects RLS tenant filter).

        Returns:
            Total number of entities.
        """
        stmt = select(func.count()).select_from(self.model_class)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, entity: ModelT) -> ModelT:
        """
        Insert a new entity into the database.

        The entity is added to the session and flushed (but not committed).
        The flush triggers server-side defaults (e.g., uuid_generate_v4(),
        NOW()) and makes the entity's generated fields available.

        Args:
            entity: The ORM model instance to insert.

        Returns:
            The same entity instance with server-generated fields populated.
        """
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def update(
        self,
        entity: ModelT,
        update_data: dict[str, Any],
    ) -> ModelT:
        """
        Partially update an existing entity.

        Only fields present in update_data are modified. Fields not in
        the dict are left unchanged.

        Args:
            entity: The ORM model instance to update.
            update_data: Dictionary of field_name → new_value.

        Returns:
            The updated entity instance.
        """
        for field, value in update_data.items():
            if hasattr(entity, field):
                setattr(entity, field, value)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        """
        Remove an entity from the database.

        The deletion is flushed but not committed until the session
        lifecycle manager commits the transaction.

        Args:
            entity: The ORM model instance to delete.
        """
        await self._session.delete(entity)
        await self._session.flush()
