"""
AtlasOS FastAPI Dependencies.

Provides injectable dependencies for authentication, authorization,
and tenant context resolution. These dependencies form the security
backbone of the API — every protected endpoint uses them.

Dependency chain:
  1. get_db_session() → AsyncSession (from core.database)
  2. get_current_user() → User (validates JWT from Authorization header)
  3. get_current_active_user() → User (additionally checks is_active)
  4. get_tenant_context() → TenantContext (extracts tenant_id from JWT claims)
  5. require_role() → Callable dependency factory for RBAC

The TenantContext dataclass carries the resolved tenant_id, user_id,
and role through the request lifecycle. It is used by:
  - The database session dependency to set RLS context via SET LOCAL.
  - API route handlers for tenant-scoped operations.
  - The audit logging service to record WHO did WHAT.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
)
from app.core.security import decode_token
from app.models.auth import ApiKey
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.auth import AuthService

# HTTP Bearer token extractor — auto_error=False so we can provide
# custom error messages instead of FastAPI's default 403.
_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class TenantContext:
    """
    Immutable context for the current tenant-scoped request.

    Carries all identity information needed for authorization and auditing.
    Frozen to prevent accidental mutation during request processing.
    """

    tenant_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    is_api_key: bool = False
    api_key_id: uuid.UUID | None = None
    permissions: list[str] | None = None


async def get_db_session_no_tenant() -> Any:
    """
    Provide a database session WITHOUT tenant RLS context.

    Used for operations that are not tenant-scoped:
      - User login (lookup by email across all tenants)
      - User registration
      - OAuth callback processing

    Yields:
        AsyncSession: A request-scoped database session without RLS.
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db_session_with_tenant(
    tenant_ctx: TenantContext = Depends(lambda: None),
) -> Any:
    """
    Provide a database session WITH tenant RLS context.

    Sets the PostgreSQL session variable `app.current_tenant_id` for
    Row-Level Security enforcement. This is the session used by all
    tenant-scoped endpoints.

    Yields:
        AsyncSession: A tenant-scoped database session.
    """
    from sqlalchemy import text

    session = async_session_factory()
    try:
        if tenant_ctx is not None:
            await session.execute(
                text("SET LOCAL app.current_tenant_id = :tenant_id"),
                {"tenant_id": str(tenant_ctx.tenant_id)},
            )
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_db_session_no_tenant),
) -> User:
    """
    Extract and validate the current user from the JWT access token.

    This dependency:
      1. Extracts the Bearer token from the Authorization header.
      2. Decodes and validates the JWT signature and expiry.
      3. Loads the User from the database.
      4. Verifies the user exists and is active.

    Args:
        credentials: Bearer token from the Authorization header.
        session: Database session for user lookup.

    Returns:
        The authenticated User instance.

    Raises:
        AuthenticationError: If no token, invalid token, or inactive user.
    """
    if credentials is None:
        raise AuthenticationError(
            message="Authentication required. Provide a Bearer token.",
        )

    payload = decode_token(credentials.credentials)

    if payload.get("type") != "access":
        raise AuthenticationError(
            message="Invalid token type. Expected an access token.",
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AuthenticationError(message="Invalid token: missing subject.")

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(uuid.UUID(user_id_str))

    if user is None:
        raise AuthenticationError(message="User not found.")
    if not user.is_active:
        raise AuthenticationError(message="User account has been deactivated.")

    return user


async def get_tenant_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    session: AsyncSession = Depends(get_db_session_no_tenant),
) -> TenantContext:
    """
    Resolve the tenant context from either a JWT or an API key.

    Authentication methods (in priority order):
      1. X-API-Key header → API key authentication (SDK/agent access).
      2. Authorization: Bearer → JWT authentication (console access).

    The resolved TenantContext is used by downstream dependencies to:
      - Set the RLS session variable.
      - Authorize endpoint access based on role/permissions.
      - Record audit log entries.

    Args:
        request: The FastAPI Request object.
        credentials: Optional Bearer token.
        x_api_key: Optional API key from X-API-Key header.
        session: Database session.

    Returns:
        TenantContext with resolved tenant_id, user_id, and role.

    Raises:
        AuthenticationError: If neither auth method provides valid credentials.
    """
    # Priority 1: API Key
    if x_api_key is not None:
        auth_service = AuthService(session)
        api_key: ApiKey = await auth_service.authenticate_api_key(x_api_key)
        return TenantContext(
            tenant_id=api_key.tenant_id,
            user_id=api_key.created_by or uuid.UUID(int=0),
            role="api_key",
            is_api_key=True,
            api_key_id=api_key.id,
            permissions=list(api_key.permissions) if api_key.permissions else [],
        )

    # Priority 2: JWT Bearer Token
    if credentials is not None:
        payload = decode_token(credentials.credentials)

        if payload.get("type") != "access":
            raise AuthenticationError(
                message="Invalid token type. Expected an access token.",
            )

        user_id_str = payload.get("sub")
        tenant_id_str = payload.get("tenant_id")
        role = payload.get("role")

        if not user_id_str:
            raise AuthenticationError(message="Invalid token: missing subject.")

        if not tenant_id_str:
            raise AuthenticationError(
                message="No tenant context in token. Use the tenant switch endpoint first.",
            )

        # Verify user exists and is active
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(uuid.UUID(user_id_str))
        if user is None or not user.is_active:
            raise AuthenticationError(message="User not found or deactivated.")

        return TenantContext(
            tenant_id=uuid.UUID(tenant_id_str),
            user_id=uuid.UUID(user_id_str),
            role=role or "member",
        )

    raise AuthenticationError(
        message="Authentication required. Provide a Bearer token or X-API-Key header.",
    )


def require_role(*allowed_roles: str) -> Any:
    """
    Factory that creates a dependency enforcing role-based access control.

    Usage in route definitions:
        @router.post("/admin-only", dependencies=[Depends(require_role("admin"))])

    Args:
        allowed_roles: Roles permitted to access the endpoint.

    Returns:
        A FastAPI dependency function.
    """

    async def _check_role(
        tenant_ctx: TenantContext = Depends(get_tenant_context),
    ) -> TenantContext:
        # API keys bypass role checks — they use permissions instead
        if tenant_ctx.is_api_key:
            return tenant_ctx

        if tenant_ctx.role not in allowed_roles:
            raise AuthorizationError(
                message=f"This action requires one of these roles: {', '.join(allowed_roles)}.",
                detail={
                    "current_role": tenant_ctx.role,
                    "required_roles": list(allowed_roles),
                },
            )
        return tenant_ctx

    return _check_role


def require_permission(*required_permissions: str) -> Any:
    """
    Factory that creates a dependency enforcing API key permission checks.

    Usage in route definitions:
        @router.post("/memories", dependencies=[Depends(require_permission("memory:write"))])

    Args:
        required_permissions: Permission scopes required for the endpoint.

    Returns:
        A FastAPI dependency function.
    """

    async def _check_permission(
        tenant_ctx: TenantContext = Depends(get_tenant_context),
    ) -> TenantContext:
        if not tenant_ctx.is_api_key:
            # JWT users bypass permission checks — they use role checks
            return tenant_ctx

        if tenant_ctx.permissions is None:
            raise AuthorizationError(message="API key has no permissions.")

        missing = set(required_permissions) - set(tenant_ctx.permissions)
        if missing:
            raise AuthorizationError(
                message=f"API key missing required permissions: {', '.join(sorted(missing))}.",
                detail={
                    "missing_permissions": list(missing),
                    "key_permissions": tenant_ctx.permissions,
                },
            )
        return tenant_ctx

    return _check_permission
