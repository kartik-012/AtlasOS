"""
AtlasOS Authentication Service.

Orchestrates all authentication flows: email/password login, JWT lifecycle,
API key lifecycle, and session management. This is the central point for
all identity verification operations.

Design decisions:
  - Service layer owns business logic; repositories own data access.
  - Password verification happens here (not in the repository) because
    it's a business rule, not a data access pattern.
  - JWT token creation is delegated to core.security for separation of
    concerns. The service decides WHEN to create tokens; security
    decides HOW.
  - API key authentication is prefix-optimized: we first filter by prefix
    (fast index lookup), then verify the hash against matching candidates
    (expensive bcrypt). This avoids scanning all keys.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
)
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    hash_password,
    verify_api_key,
    verify_password,
)
from app.repositories.auth import ApiKeyRepository, SessionRepository
from app.repositories.tenant import TenantMembershipRepository
from app.repositories.user import UserRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.auth import ApiKey
    from app.models.user import User

logger = get_logger(__name__)


class AuthService:
    """
    Service for authentication and authorization operations.

    All methods operate within the context of the injected database session.
    The session transaction lifecycle (commit/rollback) is managed by the
    FastAPI dependency, not by this service.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._user_repo = UserRepository(session)
        self._api_key_repo = ApiKeyRepository(session)
        self._session_repo = SessionRepository(session)
        self._membership_repo = TenantMembershipRepository(session)

    # =========================================================================
    # Email/Password Authentication
    # =========================================================================

    async def register_user(
        self,
        email: str,
        password: str,
        display_name: str,
    ) -> User:
        """
        Register a new user with email/password credentials.

        Checks for email uniqueness before creating the account.

        Args:
            email: User's email address.
            password: Plaintext password (will be hashed).
            display_name: Display name for the console.

        Returns:
            The newly created User instance.

        Raises:
            ConflictError: If the email is already registered.
        """
        existing = await self._user_repo.get_by_email(email)
        if existing is not None:
            raise ConflictError(
                message="An account with this email already exists.",
                detail={"email": email},
            )

        password_hash = hash_password(password)
        user = await self._user_repo.create_user(
            email=email,
            display_name=display_name,
            password_hash=password_hash,
        )
        logger.info(
            "user_registered",
            user_id=str(user.id),
            email=email,
        )
        return user

    async def login_with_password(
        self,
        email: str,
        password: str,
    ) -> tuple[User, str, str]:
        """
        Authenticate a user with email and password.

        Returns the user and a JWT token pair (access + refresh).

        Args:
            email: Registered email address.
            password: Plaintext password.

        Returns:
            Tuple of (User, access_token, refresh_token).

        Raises:
            AuthenticationError: If credentials are invalid.
        """
        user = await self._user_repo.get_by_email(email)
        if user is None:
            raise AuthenticationError(
                message="Invalid email or password.",
            )

        if user.password_hash is None:
            raise AuthenticationError(
                message="This account uses OAuth login. Please sign in with your linked provider.",
            )

        if not verify_password(password, user.password_hash):
            raise AuthenticationError(
                message="Invalid email or password.",
            )

        if not user.is_active:
            raise AuthenticationError(
                message="This account has been deactivated.",
            )

        await self._user_repo.update_last_login(user)

        memberships = await self._membership_repo.get_user_memberships(user.id)
        if memberships:
            membership = memberships[0]
            access_token = create_access_token(
                subject=str(user.id),
                tenant_id=str(membership.tenant_id),
                role=membership.role,
            )
        else:
            access_token = create_access_token(subject=str(user.id))

        refresh_token = create_refresh_token(subject=str(user.id))

        logger.info(
            "user_logged_in",
            user_id=str(user.id),
            method="password",
            tenant_scoped=bool(memberships),
        )
        return user, access_token, refresh_token

    async def refresh_access_token(
        self,
        refresh_token_str: str,
    ) -> tuple[str, str]:
        """
        Exchange a valid refresh token for a new access/refresh token pair.

        Args:
            refresh_token_str: The refresh token JWT string.

        Returns:
            Tuple of (new_access_token, new_refresh_token).

        Raises:
            AuthenticationError: If the refresh token is invalid or the user
                                 no longer exists/is inactive.
        """
        payload = decode_token(refresh_token_str)

        if payload.get("type") != "refresh":
            raise AuthenticationError(
                message="Invalid token type. Expected a refresh token.",
            )

        user_id = payload.get("sub")
        if user_id is None:
            raise AuthenticationError(message="Invalid token: missing subject.")

        user = await self._user_repo.get_by_id(uuid.UUID(user_id))
        if user is None or not user.is_active:
            raise AuthenticationError(
                message="User account not found or deactivated.",
            )

        new_access = create_access_token(subject=str(user.id))
        new_refresh = create_refresh_token(subject=str(user.id))
        return new_access, new_refresh

    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
    ) -> None:
        """
        Change a user's password after verifying the current one.

        Args:
            user: The authenticated User instance.
            current_password: Current password for verification.
            new_password: New password to set.

        Raises:
            AuthenticationError: If current password is wrong.
        """
        if user.password_hash is None or not verify_password(current_password, user.password_hash):
            raise AuthenticationError(
                message="Current password is incorrect.",
            )

        new_hash = hash_password(new_password)
        await self._user_repo.set_password(user, new_hash)
        logger.info("password_changed", user_id=str(user.id))

    # =========================================================================
    # JWT Token Validation
    # =========================================================================

    async def get_user_from_token(self, token: str) -> User:
        """
        Validate a JWT access token and return the associated user.

        Args:
            token: JWT access token string.

        Returns:
            The authenticated User instance.

        Raises:
            AuthenticationError: If the token is invalid or the user is inactive.
        """
        payload = decode_token(token)

        if payload.get("type") != "access":
            raise AuthenticationError(
                message="Invalid token type. Expected an access token.",
            )

        user_id = payload.get("sub")
        if user_id is None:
            raise AuthenticationError(message="Invalid token: missing subject.")

        user = await self._user_repo.get_by_id(uuid.UUID(user_id))
        if user is None:
            raise AuthenticationError(message="User not found.")
        if not user.is_active:
            raise AuthenticationError(message="User account has been deactivated.")

        return user

    # =========================================================================
    # API Key Authentication
    # =========================================================================

    async def create_api_key(
        self,
        tenant_id: uuid.UUID,
        name: str,
        permissions: list[str],
        created_by: uuid.UUID | None = None,
        expires_at: datetime | None = None,
    ) -> tuple[ApiKey, str]:
        """
        Generate a new API key for a tenant.

        Returns the ApiKey record AND the plaintext key. The plaintext key
        is shown to the user exactly once — it is never stored or logged.

        Args:
            tenant_id: Owning tenant UUID.
            name: Human-readable key name.
            permissions: List of permission scopes.
            created_by: UUID of the creating user.
            expires_at: Optional expiration datetime.

        Returns:
            Tuple of (ApiKey record, plaintext_key).
        """
        prefix, plaintext_key, key_hash = generate_api_key()

        api_key = await self._api_key_repo.create_api_key(
            tenant_id=tenant_id,
            name=name,
            key_prefix=prefix,
            key_hash=key_hash,
            permissions=permissions,
            created_by=created_by,
            expires_at=expires_at,
        )

        logger.info(
            "api_key_created",
            key_id=str(api_key.id),
            tenant_id=str(tenant_id),
            key_prefix=prefix,
        )
        return api_key, plaintext_key

    async def authenticate_api_key(self, raw_key: str) -> ApiKey:
        """
        Authenticate a request using an API key.

        Optimized flow:
          1. Extract the prefix (first 8 chars) from the raw key.
          2. Query the database for active keys matching that prefix.
          3. Verify the raw key against each candidate's bcrypt hash.
          4. Check expiration.

        Args:
            raw_key: The plaintext API key from the request header.

        Returns:
            The authenticated ApiKey instance.

        Raises:
            AuthenticationError: If the key is invalid, revoked, or expired.
        """
        if len(raw_key) < 8:
            raise AuthenticationError(message="Invalid API key format.")

        prefix = raw_key[:8]
        candidates = await self._api_key_repo.get_by_prefix(prefix)

        if not candidates:
            raise AuthenticationError(message="Invalid API key.")

        for candidate in candidates:
            if verify_api_key(raw_key, candidate.key_hash):
                # Check expiration
                if candidate.expires_at is not None:
                    if candidate.expires_at < datetime.now(UTC):
                        raise AuthenticationError(
                            message="API key has expired.",
                        )
                # Update last_used_at
                await self._api_key_repo.update_last_used(candidate)
                return candidate

        raise AuthenticationError(message="Invalid API key.")

    async def revoke_api_key(
        self,
        key_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> ApiKey:
        """
        Revoke an API key.

        Args:
            key_id: UUID of the key to revoke.
            tenant_id: Tenant UUID (for authorization check).

        Returns:
            The revoked ApiKey instance.

        Raises:
            NotFoundError: If the key does not exist.
        """
        api_key = await self._api_key_repo.get_by_id(key_id)
        if api_key is None or api_key.tenant_id != tenant_id:
            raise NotFoundError(
                message="API key not found.",
                detail={"key_id": str(key_id)},
            )

        revoked = await self._api_key_repo.revoke_key(api_key)
        logger.info(
            "api_key_revoked",
            key_id=str(key_id),
            tenant_id=str(tenant_id),
        )
        return revoked

    # =========================================================================
    # Token with Tenant Context
    # =========================================================================

    async def create_tenant_scoped_token(
        self,
        user: User,
        tenant_id: uuid.UUID,
    ) -> tuple[str, str]:
        """
        Create a JWT token pair scoped to a specific tenant.

        Verifies the user is a member of the tenant and embeds the
        tenant_id and role into the access token claims.

        Args:
            user: The authenticated User instance.
            tenant_id: The tenant to scope the token to.

        Returns:
            Tuple of (access_token, refresh_token).

        Raises:
            AuthorizationError: If the user is not a member of the tenant.
        """
        membership = await self._membership_repo.get_membership(
            tenant_id=tenant_id,
            user_id=user.id,
        )
        if membership is None:
            raise AuthorizationError(
                message="You are not a member of this tenant.",
                detail={"tenant_id": str(tenant_id)},
            )

        access_token = create_access_token(
            subject=str(user.id),
            tenant_id=str(tenant_id),
            role=membership.role,
        )
        refresh_token = create_refresh_token(subject=str(user.id))
        return access_token, refresh_token
