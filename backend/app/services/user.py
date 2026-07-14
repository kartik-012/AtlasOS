"""
AtlasOS User Service.

Business logic for user profile management. User registration is handled
by AuthService (since it's an authentication operation). This service
handles post-registration profile operations.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.user import User
from app.repositories.tenant import TenantMembershipRepository
from app.repositories.user import UserRepository
from app.schemas.user import UserTenantInfo

logger = get_logger(__name__)


class UserService:
    """Service for user profile operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._user_repo = UserRepository(session)
        self._membership_repo = TenantMembershipRepository(session)

    async def get_user(self, user_id: uuid.UUID) -> User:
        """
        Get a user by ID.

        Args:
            user_id: The user UUID.

        Returns:
            The User instance.

        Raises:
            NotFoundError: If the user does not exist.
        """
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError(
                message="User not found.",
                detail={"user_id": str(user_id)},
            )
        return user

    async def update_profile(
        self,
        user_id: uuid.UUID,
        update_data: dict[str, Any],
    ) -> User:
        """
        Update user profile fields.

        Args:
            user_id: The user UUID.
            update_data: Dictionary of fields to update.

        Returns:
            The updated User instance.

        Raises:
            NotFoundError: If the user does not exist.
        """
        user = await self.get_user(user_id)
        filtered = {k: v for k, v in update_data.items() if v is not None}
        if not filtered:
            return user

        updated = await self._user_repo.update(user, filtered)
        logger.info("user_profile_updated", user_id=str(user_id), fields=list(filtered.keys()))
        return updated

    async def get_user_tenants(self, user_id: uuid.UUID) -> list[UserTenantInfo]:
        """
        Get all tenants the user is a member of.

        Args:
            user_id: The user UUID.

        Returns:
            List of UserTenantInfo schemas.
        """
        memberships = await self._membership_repo.get_user_memberships(user_id)
        return [
            UserTenantInfo(
                tenant_id=m.tenant_id,
                tenant_name=m.tenant.name,
                tenant_slug=m.tenant.slug,
                role=m.role,
                joined_at=m.joined_at,
            )
            for m in memberships
        ]
