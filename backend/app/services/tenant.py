"""
AtlasOS Tenant Service.

Business logic for tenant lifecycle management: creation, updates,
membership management, and team invitations.

Design decisions:
  - Tenant creation automatically assigns the creating user as the
    admin of the new tenant. Every tenant must have at least one admin.
  - Slug uniqueness is checked before creation to provide a clear error
    message instead of a database constraint violation.
  - Member removal enforces the "last admin" rule — the last admin of
    a tenant cannot be removed or demoted to prevent orphaned tenants.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.logging import get_logger
from app.core.security import generate_session_token, hash_session_token
from app.models.auth import TenantMembership
from app.models.tenant import Tenant
from app.repositories.auth import TeamInviteRepository
from app.repositories.tenant import TenantMembershipRepository, TenantRepository

logger = get_logger(__name__)


class TenantService:
    """
    Service for tenant lifecycle and membership management.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._tenant_repo = TenantRepository(session)
        self._membership_repo = TenantMembershipRepository(session)
        self._invite_repo = TeamInviteRepository(session)

    # =========================================================================
    # Tenant CRUD
    # =========================================================================

    async def create_tenant(
        self,
        name: str,
        slug: str,
        creator_user_id: uuid.UUID,
    ) -> Tenant:
        """
        Create a new tenant workspace and assign the creator as admin.

        Args:
            name: Human-readable tenant name.
            slug: URL-safe unique identifier.
            creator_user_id: UUID of the user creating the tenant.

        Returns:
            The newly created Tenant instance.

        Raises:
            ConflictError: If the slug is already taken.
        """
        if await self._tenant_repo.slug_exists(slug):
            raise ConflictError(
                message=f"A tenant with slug '{slug}' already exists.",
                detail={"slug": slug},
            )

        tenant = await self._tenant_repo.create_tenant(name=name, slug=slug)

        # Assign creator as admin
        await self._membership_repo.create_membership(
            tenant_id=tenant.id,
            user_id=creator_user_id,
            role="admin",
        )

        logger.info(
            "tenant_created",
            tenant_id=str(tenant.id),
            slug=slug,
            creator_id=str(creator_user_id),
        )
        return tenant

    async def get_tenant(self, tenant_id: uuid.UUID) -> Tenant:
        """
        Get a tenant by ID.

        Args:
            tenant_id: The tenant UUID.

        Returns:
            The Tenant instance.

        Raises:
            NotFoundError: If the tenant does not exist.
        """
        tenant = await self._tenant_repo.get_by_id(tenant_id)
        if tenant is None:
            raise NotFoundError(
                message="Tenant not found.",
                detail={"tenant_id": str(tenant_id)},
            )
        return tenant

    async def update_tenant(
        self,
        tenant_id: uuid.UUID,
        update_data: dict[str, Any],
    ) -> Tenant:
        """
        Update tenant settings.

        Args:
            tenant_id: The tenant UUID.
            update_data: Dictionary of fields to update.

        Returns:
            The updated Tenant instance.

        Raises:
            NotFoundError: If the tenant does not exist.
        """
        tenant = await self.get_tenant(tenant_id)
        # Filter out None values — only update provided fields
        filtered = {k: v for k, v in update_data.items() if v is not None}
        if not filtered:
            return tenant

        updated = await self._tenant_repo.update(tenant, filtered)
        logger.info(
            "tenant_updated",
            tenant_id=str(tenant_id),
            fields=list(filtered.keys()),
        )
        return updated

    # =========================================================================
    # Membership Management
    # =========================================================================

    async def get_members(
        self,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> list[TenantMembership]:
        """
        List all members of a tenant.

        Args:
            tenant_id: The tenant UUID.
            offset: Pagination offset.
            limit: Pagination limit.

        Returns:
            List of TenantMembership instances with User loaded.
        """
        return await self._membership_repo.get_tenant_members(
            tenant_id=tenant_id,
            offset=offset,
            limit=limit,
        )

    async def update_member_role(
        self,
        tenant_id: uuid.UUID,
        target_user_id: uuid.UUID,
        new_role: str,
        requesting_user_id: uuid.UUID,
    ) -> TenantMembership:
        """
        Update a team member's role.

        Enforces the "last admin" rule: cannot demote the last admin.

        Args:
            tenant_id: The tenant UUID.
            target_user_id: UUID of the member to update.
            new_role: New role to assign.
            requesting_user_id: UUID of the user making the request.

        Returns:
            The updated TenantMembership instance.

        Raises:
            NotFoundError: If the membership does not exist.
            ValidationError: If this would remove the last admin.
            AuthorizationError: If the requesting user is not an admin.
        """
        # Verify requester is admin
        requester_membership = await self._membership_repo.get_membership(
            tenant_id=tenant_id,
            user_id=requesting_user_id,
        )
        if requester_membership is None or requester_membership.role != "admin":
            raise AuthorizationError(
                message="Only admins can change member roles.",
            )

        # Get target membership
        target_membership = await self._membership_repo.get_membership(
            tenant_id=tenant_id,
            user_id=target_user_id,
        )
        if target_membership is None:
            raise NotFoundError(
                message="Member not found in this tenant.",
                detail={"user_id": str(target_user_id)},
            )

        # Prevent removing the last admin
        if target_membership.role == "admin" and new_role != "admin":
            all_members = await self._membership_repo.get_tenant_members(
                tenant_id=tenant_id,
            )
            admin_count = sum(1 for m in all_members if m.role == "admin")
            if admin_count <= 1:
                raise ValidationError(
                    message="Cannot demote the last admin. Promote another member to admin first.",
                )

        updated = await self._membership_repo.update_role(target_membership, new_role)
        logger.info(
            "member_role_updated",
            tenant_id=str(tenant_id),
            target_user_id=str(target_user_id),
            new_role=new_role,
        )
        return updated

    async def remove_member(
        self,
        tenant_id: uuid.UUID,
        target_user_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
    ) -> None:
        """
        Remove a member from a tenant.

        Enforces the "last admin" rule.

        Args:
            tenant_id: The tenant UUID.
            target_user_id: UUID of the member to remove.
            requesting_user_id: UUID of the requesting user.

        Raises:
            NotFoundError: If the membership does not exist.
            ValidationError: If removing the last admin.
            AuthorizationError: If requester lacks permission.
        """
        # Admins can remove anyone; members can remove themselves
        requester = await self._membership_repo.get_membership(
            tenant_id=tenant_id,
            user_id=requesting_user_id,
        )
        if requester is None:
            raise AuthorizationError(message="You are not a member of this tenant.")

        is_self_removal = target_user_id == requesting_user_id
        if not is_self_removal and requester.role != "admin":
            raise AuthorizationError(
                message="Only admins can remove other members.",
            )

        target = await self._membership_repo.get_membership(
            tenant_id=tenant_id,
            user_id=target_user_id,
        )
        if target is None:
            raise NotFoundError(message="Member not found in this tenant.")

        # Last admin check
        if target.role == "admin":
            all_members = await self._membership_repo.get_tenant_members(
                tenant_id=tenant_id,
            )
            admin_count = sum(1 for m in all_members if m.role == "admin")
            if admin_count <= 1:
                raise ValidationError(
                    message="Cannot remove the last admin. Transfer ownership first.",
                )

        await self._membership_repo.delete(target)
        logger.info(
            "member_removed",
            tenant_id=str(tenant_id),
            removed_user_id=str(target_user_id),
        )

    # =========================================================================
    # Team Invitations
    # =========================================================================

    async def create_invite(
        self,
        tenant_id: uuid.UUID,
        email: str,
        role: str,
        invited_by: uuid.UUID,
    ) -> tuple[Any, str]:
        """
        Create a team invitation.

        Generates a secure token, hashes it for storage, and returns
        the plaintext token for the invitation email.

        Args:
            tenant_id: The tenant UUID.
            email: Invitee email address.
            role: Role to assign upon acceptance.
            invited_by: UUID of the inviting user.

        Returns:
            Tuple of (TeamInvite record, plaintext_invite_token).

        Raises:
            ConflictError: If the user is already a member or has a pending invite.
        """
        # Check for existing membership
        from app.repositories.user import UserRepository
        user_repo = UserRepository(self._session)
        existing_user = await user_repo.get_by_email(email)
        if existing_user is not None:
            existing_membership = await self._membership_repo.get_membership(
                tenant_id=tenant_id,
                user_id=existing_user.id,
            )
            if existing_membership is not None:
                raise ConflictError(
                    message="This user is already a member of the tenant.",
                    detail={"email": email},
                )

        # Check for existing pending invite
        pending = await self._invite_repo.get_pending_invites_for_tenant(tenant_id)
        for inv in pending:
            if inv.email == email.lower():
                raise ConflictError(
                    message="A pending invitation already exists for this email.",
                    detail={"email": email},
                )

        plaintext_token, token_hash = generate_session_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        invite = await self._invite_repo.create_invite(
            tenant_id=tenant_id,
            email=email,
            role=role,
            token_hash=token_hash,
            expires_at=expires_at,
            invited_by=invited_by,
        )

        logger.info(
            "team_invite_created",
            tenant_id=str(tenant_id),
            email=email,
            role=role,
        )
        return invite, plaintext_token

    async def accept_invite(
        self,
        token: str,
        user_id: uuid.UUID,
    ) -> TenantMembership:
        """
        Accept a team invitation using the invitation token.

        Args:
            token: Plaintext invitation token.
            user_id: UUID of the accepting user.

        Returns:
            The newly created TenantMembership.

        Raises:
            NotFoundError: If the invitation is not found.
            ValidationError: If the invitation is expired or not pending.
        """
        token_hash = hash_session_token(token)
        invite = await self._invite_repo.get_by_token_hash(token_hash)

        if invite is None:
            raise NotFoundError(message="Invitation not found or invalid token.")

        if invite.status != "pending":
            raise ValidationError(
                message=f"Invitation has already been {invite.status}.",
            )

        if invite.expires_at < datetime.now(timezone.utc):
            await self._invite_repo.update(invite, {"status": "expired"})
            raise ValidationError(message="Invitation has expired.")

        # Create membership
        membership = await self._membership_repo.create_membership(
            tenant_id=invite.tenant_id,
            user_id=user_id,
            role=invite.role,
            invited_by=invite.invited_by,
        )

        # Mark invite as accepted
        await self._invite_repo.mark_accepted(invite)

        logger.info(
            "team_invite_accepted",
            tenant_id=str(invite.tenant_id),
            user_id=str(user_id),
            role=invite.role,
        )
        return membership
