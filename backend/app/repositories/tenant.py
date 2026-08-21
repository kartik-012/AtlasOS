"""
AtlasOS Tenant Repository.

Handles all database operations for the tenants table and the
tenant_memberships table.

Both tables are tenant-scoped (memberships via RLS), but tenants
themselves are the root entity that defines the scope.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.auth import TenantMembership
from app.models.tenant import Tenant
from app.repositories.base import BaseRepository

if TYPE_CHECKING:
    import uuid


class TenantRepository(BaseRepository[Tenant]):
    """Repository for Tenant CRUD operations."""

    model_class = Tenant

    async def get_by_slug(self, slug: str) -> Tenant | None:
        """
        Fetch a tenant by its URL-safe slug.

        Args:
            slug: The tenant's unique slug.

        Returns:
            The Tenant instance, or None if not found.
        """
        stmt = select(Tenant).where(Tenant.slug == slug)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def slug_exists(self, slug: str) -> bool:
        """
        Check if a tenant slug is already taken.

        Args:
            slug: The slug to check.

        Returns:
            True if the slug exists, False otherwise.
        """
        tenant = await self.get_by_slug(slug)
        return tenant is not None

    async def create_tenant(
        self,
        name: str,
        slug: str,
    ) -> Tenant:
        """
        Create a new tenant workspace with default settings.

        Args:
            name: Human-readable tenant name.
            slug: URL-safe unique identifier.

        Returns:
            The newly created Tenant instance.
        """
        tenant = Tenant(
            name=name,
            slug=slug,
        )
        return await self.create(tenant)


class TenantMembershipRepository(BaseRepository[TenantMembership]):
    """Repository for TenantMembership operations."""

    model_class = TenantMembership

    async def get_membership(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> TenantMembership | None:
        """
        Get a specific user's membership in a tenant.

        Args:
            tenant_id: The tenant UUID.
            user_id: The user UUID.

        Returns:
            The TenantMembership instance, or None if the user is not a member.
        """
        stmt = select(TenantMembership).where(
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_memberships(
        self,
        user_id: uuid.UUID,
    ) -> list[TenantMembership]:
        """
        Get all tenant memberships for a user.

        Loads the related Tenant eagerly to avoid N+1 queries when
        building the user's tenant list.

        Args:
            user_id: The user UUID.

        Returns:
            List of TenantMembership instances with Tenant loaded.
        """
        stmt = (
            select(TenantMembership)
            .options(selectinload(TenantMembership.tenant))
            .where(TenantMembership.user_id == user_id)
            .order_by(TenantMembership.joined_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    get_memberships_for_user = get_user_memberships

    async def get_tenant_members(
        self,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> list[TenantMembership]:
        """
        Get all members of a tenant with their User data loaded.

        Args:
            tenant_id: The tenant UUID.
            offset: Pagination offset.
            limit: Pagination limit.

        Returns:
            List of TenantMembership instances with User loaded.
        """
        stmt = (
            select(TenantMembership)
            .options(selectinload(TenantMembership.user))
            .where(TenantMembership.tenant_id == tenant_id)
            .offset(offset)
            .limit(limit)
            .order_by(TenantMembership.joined_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create_membership(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str = "admin",
        invited_by: uuid.UUID | None = None,
    ) -> TenantMembership:
        """
        Create a new tenant membership.

        Args:
            tenant_id: The tenant UUID.
            user_id: The user UUID.
            role: The role to assign (admin, member, read_only).
            invited_by: UUID of the user who sent the invitation.

        Returns:
            The newly created TenantMembership instance.
        """
        membership = TenantMembership(
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
            invited_by=invited_by,
        )
        return await self.create(membership)

    async def update_role(
        self,
        membership: TenantMembership,
        new_role: str,
    ) -> TenantMembership:
        """
        Update a member's role within a tenant.

        Args:
            membership: The membership to update.
            new_role: The new role to assign.

        Returns:
            The updated TenantMembership instance.
        """
        return await self.update(membership, {"role": new_role})
