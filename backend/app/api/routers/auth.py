"""
AtlasOS Authentication API Router.

Exposes endpoints for user registration, email/password login, token refresh,
OAuth2 flows, and API key management.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, status

from app.core.config import get_settings
from app.core.dependencies import (
    TenantContext,
    get_current_user,
    get_db_session_no_tenant,
    get_db_session_with_tenant,
    get_tenant_context,
    require_role,
)
from app.schemas.auth import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyResponse,
    ApiKeyRevokeRequest,
    LoginRequest,
    OAuthCallbackRequest,
    OAuthLoginResponse,
    PasswordChangeRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserRegisterRequest,
)
from app.schemas.user import UserResponse
from app.services.auth import AuthService
from app.services.oauth import OAuthService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


# =============================================================================
# Standard Registration & Login
# =============================================================================


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    request: UserRegisterRequest,
    session: AsyncSession = Depends(get_db_session_no_tenant),
) -> User:
    auth_service = AuthService(session)
    return await auth_service.register_user(
        email=request.email,
        password=request.password,
        display_name=request.display_name,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email and password",
)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_db_session_no_tenant),
) -> TokenResponse:
    auth_service = AuthService(session)
    _user, access_token, refresh_token = await auth_service.login_with_password(
        email=request.email,
        password=request.password,
    )
    settings = get_settings()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh_token(
    request: TokenRefreshRequest,
    session: AsyncSession = Depends(get_db_session_no_tenant),
) -> TokenResponse:
    auth_service = AuthService(session)
    new_access, new_refresh = await auth_service.refresh_access_token(
        refresh_token_str=request.refresh_token,
    )
    settings = get_settings()
    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change current user password",
)
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session_no_tenant),
) -> None:
    auth_service = AuthService(session)
    await auth_service.change_password(
        user=current_user,
        current_password=request.current_password,
        new_password=request.new_password,
    )


# =============================================================================
# OAuth2 Flows
# =============================================================================


@router.get(
    "/google/login",
    response_model=OAuthLoginResponse,
    summary="Get Google OAuth2 authorization URL",
)
async def google_login(
    redirect_uri: str,
    session: AsyncSession = Depends(get_db_session_no_tenant),
) -> OAuthLoginResponse:
    oauth_service = OAuthService(session)
    url, _ = oauth_service.get_google_authorization_url(redirect_uri=redirect_uri)
    return OAuthLoginResponse(authorization_url=url)


@router.post(
    "/google/callback",
    response_model=TokenResponse,
    summary="Handle Google OAuth2 callback",
)
async def google_callback(
    redirect_uri: str,
    request: OAuthCallbackRequest,
    session: AsyncSession = Depends(get_db_session_no_tenant),
) -> TokenResponse:
    oauth_service = OAuthService(session)
    _, access_token, refresh_token, _ = await oauth_service.handle_google_callback(
        code=request.code,
        redirect_uri=redirect_uri,
    )
    settings = get_settings()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get(
    "/github/login",
    response_model=OAuthLoginResponse,
    summary="Get GitHub OAuth2 authorization URL",
)
async def github_login(
    redirect_uri: str,
    session: AsyncSession = Depends(get_db_session_no_tenant),
) -> OAuthLoginResponse:
    oauth_service = OAuthService(session)
    url, _ = oauth_service.get_github_authorization_url(redirect_uri=redirect_uri)
    return OAuthLoginResponse(authorization_url=url)


@router.post(
    "/github/callback",
    response_model=TokenResponse,
    summary="Handle GitHub OAuth2 callback",
)
async def github_callback(
    redirect_uri: str,
    request: OAuthCallbackRequest,
    session: AsyncSession = Depends(get_db_session_no_tenant),
) -> TokenResponse:
    oauth_service = OAuthService(session)
    _, access_token, refresh_token, _ = await oauth_service.handle_github_callback(
        code=request.code,
        redirect_uri=redirect_uri,
    )
    settings = get_settings()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# =============================================================================
# API Key Management (Tenant Scoped)
# =============================================================================


@router.post(
    "/api-keys",
    response_model=ApiKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key for the current tenant",
    dependencies=[Depends(require_role("admin"))],
)
async def create_api_key(
    request: ApiKeyCreateRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session_with_tenant),
) -> ApiKeyCreateResponse:
    auth_service = AuthService(session)
    api_key, plaintext_key = await auth_service.create_api_key(
        tenant_id=tenant_ctx.tenant_id,
        name=request.name,
        permissions=request.permissions,
        created_by=tenant_ctx.user_id,
        expires_at=request.expires_at,
    )

    # We must manually construct the response because we need to inject the plaintext key
    return ApiKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        plaintext_key=plaintext_key,
        permissions=api_key.permissions,
        is_active=api_key.is_active,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


@router.get(
    "/api-keys",
    response_model=list[ApiKeyResponse],
    summary="List all API keys for the current tenant",
    dependencies=[Depends(require_role("admin", "member"))],
)
async def list_api_keys(
    skip: int = 0,
    limit: int = 50,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session_with_tenant),
) -> list[ApiKeyResponse]:
    from app.repositories.auth import ApiKeyRepository

    repo = ApiKeyRepository(session)
    return await repo.get_active_keys_for_tenant(  # type: ignore
        tenant_id=tenant_ctx.tenant_id,
        offset=skip,
        limit=limit,
    )


@router.post(
    "/api-keys/revoke",
    response_model=ApiKeyResponse,
    summary="Revoke an API key",
    dependencies=[Depends(require_role("admin"))],
)
async def revoke_api_key(
    request: ApiKeyRevokeRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session_with_tenant),
) -> ApiKeyResponse:
    auth_service = AuthService(session)
    return await auth_service.revoke_api_key(  # type: ignore
        key_id=request.key_id,
        tenant_id=tenant_ctx.tenant_id,
    )
