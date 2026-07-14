"""
AtlasOS User & OAuth Account Repositories.

Handles all database operations for the users and oauth_accounts tables.

The User model is a global entity (not tenant-scoped), so queries on this
table are NOT filtered by RLS. This is intentional — users exist across
tenants and must be queryable by email during login regardless of tenant
context.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import OAuthAccount
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User CRUD and lookup operations."""

    model_class = User

    async def get_by_email(self, email: str) -> User | None:
        """
        Fetch a user by their email address.

        Used during login and registration to check for existing accounts.

        Args:
            email: The email address to search for (case-insensitive).

        Returns:
            The User instance, or None if not found.
        """
        stmt = select(User).where(User.email == email.lower())
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(
        self,
        email: str,
        display_name: str,
        password_hash: str | None = None,
        avatar_url: str | None = None,
        email_verified: bool = False,
    ) -> User:
        """
        Create a new user account.

        Args:
            email: Unique email address.
            display_name: Display name for the console UI.
            password_hash: Bcrypt hash. None for OAuth-only accounts.
            avatar_url: Optional avatar URL from OAuth provider.
            email_verified: Whether the email is pre-verified (True for OAuth).

        Returns:
            The newly created User instance.
        """
        user = User(
            email=email.lower(),
            display_name=display_name,
            password_hash=password_hash,
            avatar_url=avatar_url,
            email_verified=email_verified,
        )
        return await self.create(user)

    async def update_last_login(self, user: User) -> User:
        """
        Update the user's last_login_at timestamp to now.

        Args:
            user: The User instance to update.

        Returns:
            The updated User instance.
        """
        return await self.update(user, {
            "last_login_at": datetime.now(timezone.utc),
        })

    async def set_password(self, user: User, password_hash: str) -> User:
        """
        Set or update a user's password hash.

        Used for password changes and for adding a password to an
        OAuth-only account.

        Args:
            user: The User instance to update.
            password_hash: New bcrypt password hash.

        Returns:
            The updated User instance.
        """
        return await self.update(user, {"password_hash": password_hash})


class OAuthAccountRepository(BaseRepository[OAuthAccount]):
    """Repository for OAuth account CRUD operations."""

    model_class = OAuthAccount

    async def get_by_provider_account(
        self,
        provider: str,
        provider_account_id: str,
    ) -> OAuthAccount | None:
        """
        Find an OAuth account by provider and provider-side account ID.

        Used during OAuth callback to check if the provider account is
        already linked to a user.

        Args:
            provider: OAuth provider name (e.g., 'google', 'github').
            provider_account_id: The user's unique ID from the provider.

        Returns:
            The OAuthAccount instance, or None if not found.
        """
        stmt = select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_account_id == provider_account_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_and_provider(
        self,
        user_id: uuid.UUID,
        provider: str,
    ) -> OAuthAccount | None:
        """
        Find a specific OAuth account for a user and provider.

        Used to check if a user already has a linked account for a
        given provider before attempting to link a new one.

        Args:
            user_id: The user's UUID.
            provider: OAuth provider name.

        Returns:
            The OAuthAccount instance, or None if not found.
        """
        stmt = select(OAuthAccount).where(
            OAuthAccount.user_id == user_id,
            OAuthAccount.provider == provider,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_oauth_account(
        self,
        user_id: uuid.UUID,
        provider: str,
        provider_account_id: str,
        provider_email: str | None = None,
        access_token_enc: str | None = None,
        refresh_token_enc: str | None = None,
        token_expires_at: datetime | None = None,
    ) -> OAuthAccount:
        """
        Link an OAuth provider account to a user.

        Args:
            user_id: The user to link the OAuth account to.
            provider: OAuth provider name.
            provider_account_id: Provider-side unique user ID.
            provider_email: Email from the provider (may differ from User.email).
            access_token_enc: Encrypted OAuth access token.
            refresh_token_enc: Encrypted OAuth refresh token.
            token_expires_at: When the access token expires.

        Returns:
            The newly created OAuthAccount instance.
        """
        oauth_account = OAuthAccount(
            user_id=user_id,
            provider=provider,
            provider_account_id=provider_account_id,
            provider_email=provider_email,
            access_token_enc=access_token_enc,
            refresh_token_enc=refresh_token_enc,
            token_expires_at=token_expires_at,
        )
        return await self.create(oauth_account)
