"""
AtlasOS Auth Repositories.

Handles database operations for API keys, sessions, and team invitations.
All three entities are tenant-scoped and rely on RLS for isolation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models.auth import ApiKey, Session, TeamInvite
from app.repositories.base import BaseRepository

if TYPE_CHECKING:
    import uuid


class ApiKeyRepository(BaseRepository[ApiKey]):
    """Repository for API key CRUD operations."""

    model_class = ApiKey

    async def get_by_prefix(self, key_prefix: str) -> list[ApiKey]:
        """
        Find API keys by their prefix.

        Used during authentication to narrow down candidate keys
        before performing the bcrypt verification.

        Args:
            key_prefix: First 8 characters of the key.

        Returns:
            List of matching ApiKey instances.
        """
        stmt = select(ApiKey).where(
            ApiKey.key_prefix == key_prefix,
            ApiKey.is_active == True,  # noqa: E712 — SQLAlchemy requires == True
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_keys_for_tenant(
        self,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> list[ApiKey]:
        """
        List all API keys for a tenant (both active and revoked).

        Args:
            tenant_id: The tenant UUID.
            offset: Pagination offset.
            limit: Pagination limit.

        Returns:
            List of ApiKey instances.
        """
        stmt = (
            select(ApiKey)
            .where(ApiKey.tenant_id == tenant_id)
            .offset(offset)
            .limit(limit)
            .order_by(ApiKey.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create_api_key(
        self,
        tenant_id: uuid.UUID,
        name: str,
        key_prefix: str,
        key_hash: str,
        permissions: list[str],
        created_by: uuid.UUID | None = None,
        expires_at: datetime | None = None,
    ) -> ApiKey:
        """
        Create a new API key record.

        Args:
            tenant_id: Owning tenant UUID.
            name: Human-readable key name.
            key_prefix: First 8 characters for identification.
            key_hash: Bcrypt hash of the full key.
            permissions: List of permission scopes.
            created_by: UUID of the user who created the key.
            expires_at: Optional expiration datetime.

        Returns:
            The newly created ApiKey instance.
        """
        api_key = ApiKey(
            tenant_id=tenant_id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            permissions=permissions,
            created_by=created_by,
            expires_at=expires_at,
        )
        return await self.create(api_key)

    async def revoke_key(self, api_key: ApiKey) -> ApiKey:
        """
        Revoke an API key by setting is_active to False.

        Args:
            api_key: The ApiKey instance to revoke.

        Returns:
            The updated ApiKey instance.
        """
        return await self.update(api_key, {"is_active": False})

    async def update_last_used(self, api_key: ApiKey) -> None:
        """
        Update the last_used_at timestamp for an API key.

        Args:
            api_key: The ApiKey instance to update.
        """
        api_key.last_used_at = datetime.now(UTC)
        await self._session.flush()


class SessionRepository(BaseRepository[Session]):
    """Repository for server-side session operations."""

    model_class = Session

    async def get_by_token_hash(self, token_hash: str) -> Session | None:
        """
        Find a session by its SHA-256 token hash.

        Args:
            token_hash: SHA-256 hex digest of the session token.

        Returns:
            The Session instance, or None if not found.
        """
        stmt = select(Session).where(Session.token_hash == token_hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_sessions_for_user(
        self,
        user_id: uuid.UUID,
    ) -> list[Session]:
        """
        Get all active (non-expired, non-revoked) sessions for a user.

        Args:
            user_id: The user UUID.

        Returns:
            List of active Session instances.
        """
        now = datetime.now(UTC)
        stmt = select(Session).where(
            Session.user_id == user_id,
            Session.revoked_at.is_(None),
            Session.expires_at > now,
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create_session(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Session:
        """
        Create a new server-side session record.

        Args:
            tenant_id: The tenant UUID (current workspace).
            user_id: The user UUID.
            token_hash: SHA-256 hash of the session token.
            expires_at: Session expiration datetime.
            ip_address: Client IP address.
            user_agent: Client User-Agent header.

        Returns:
            The newly created Session instance.
        """
        session = Session(
            tenant_id=tenant_id,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return await self.create(session)

    async def revoke_session(self, session: Session) -> Session:
        """
        Revoke a session by setting revoked_at to now.

        Args:
            session: The Session instance to revoke.

        Returns:
            The updated Session instance.
        """
        return await self.update(
            session,
            {
                "revoked_at": datetime.now(UTC),
            },
        )

    async def revoke_all_user_sessions(self, user_id: uuid.UUID) -> int:
        """
        Revoke all active sessions for a user (sign out everywhere).

        Args:
            user_id: The user UUID.

        Returns:
            Number of sessions revoked.
        """
        sessions = await self.get_active_sessions_for_user(user_id)
        now = datetime.now(UTC)
        for sess in sessions:
            sess.revoked_at = now
        await self._session.flush()
        return len(sessions)


class TeamInviteRepository(BaseRepository[TeamInvite]):
    """Repository for team invitation operations."""

    model_class = TeamInvite

    async def get_by_token_hash(self, token_hash: str) -> TeamInvite | None:
        """
        Find an invitation by its SHA-256 token hash.

        Args:
            token_hash: SHA-256 hex digest of the invitation token.

        Returns:
            The TeamInvite instance, or None if not found.
        """
        stmt = select(TeamInvite).where(TeamInvite.token_hash == token_hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_pending_invites_for_tenant(
        self,
        tenant_id: uuid.UUID,
    ) -> list[TeamInvite]:
        """
        Get all pending invitations for a tenant.

        Args:
            tenant_id: The tenant UUID.

        Returns:
            List of pending TeamInvite instances.
        """
        stmt = select(TeamInvite).where(
            TeamInvite.tenant_id == tenant_id,
            TeamInvite.status == "pending",
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_invites_for_email(
        self,
        email: str,
    ) -> list[TeamInvite]:
        """
        Get all pending invitations sent to a specific email.

        Used during registration to auto-accept pending invitations.

        Args:
            email: The email address to search for.

        Returns:
            List of pending TeamInvite instances.
        """
        stmt = select(TeamInvite).where(
            TeamInvite.email == email.lower(),
            TeamInvite.status == "pending",
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create_invite(
        self,
        tenant_id: uuid.UUID,
        email: str,
        role: str,
        token_hash: str,
        expires_at: datetime,
        invited_by: uuid.UUID | None = None,
    ) -> TeamInvite:
        """
        Create a new team invitation.

        Args:
            tenant_id: The tenant UUID.
            email: Invitee email address.
            role: Role to assign upon acceptance.
            token_hash: SHA-256 hash of the invitation token.
            expires_at: When the invitation expires.
            invited_by: UUID of the inviting user.

        Returns:
            The newly created TeamInvite instance.
        """
        invite = TeamInvite(
            tenant_id=tenant_id,
            email=email.lower(),
            role=role,
            token_hash=token_hash,
            expires_at=expires_at,
            invited_by=invited_by,
        )
        return await self.create(invite)

    async def mark_accepted(self, invite: TeamInvite) -> TeamInvite:
        """
        Mark an invitation as accepted.

        Args:
            invite: The TeamInvite instance to update.

        Returns:
            The updated TeamInvite instance.
        """
        return await self.update(
            invite,
            {
                "status": "accepted",
                "accepted_at": datetime.now(UTC),
            },
        )

    async def mark_revoked(self, invite: TeamInvite) -> TeamInvite:
        """
        Mark an invitation as revoked.

        Args:
            invite: The TeamInvite instance to update.

        Returns:
            The updated TeamInvite instance.
        """
        return await self.update(invite, {"status": "revoked"})
