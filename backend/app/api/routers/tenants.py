"""
AtlasOS Tenants API Router.

Endpoints for managing tenants, memberships, and team invitations.
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
from app.schemas.auth import TokenResponse
from app.schemas.invite import (
    InviteAcceptRequest,
    InviteCreateRequest,
    InviteResponse,
    MemberRoleUpdateRequest,
)
from app.schemas.tenant import (
    TenantCreateRequest,
    TenantMemberResponse,
    TenantResponse,
    TenantUpdateRequest,
)
from app.services.auth import AuthService
from app.services.tenant import TenantService

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.post(
    "/",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tenant workspace",
)
async def create_tenant(
    request: TenantCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session_no_tenant),
) -> TenantResponse:
    tenant_service = TenantService(session)
    return await tenant_service.create_tenant(  # type: ignore
        name=request.name,
        slug=request.slug,
        creator_user_id=current_user.id,
    )


@router.get(
    "",
    response_model=list[TenantResponse],
    summary="List all accessible tenants for the user",
)
async def list_tenants(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session_no_tenant),
) -> list[TenantResponse]:
    tenant_service = TenantService(session)
    return await tenant_service.get_tenants_for_user(current_user.id)  # type: ignore


@router.get(
    "/current",
    response_model=TenantResponse,
    summary="Get current tenant details",
    dependencies=[Depends(require_role("admin", "member", "read_only"))],
)
async def get_current_tenant(
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session_with_tenant),
) -> TenantResponse:
    tenant_service = TenantService(session)
    return await tenant_service.get_tenant(tenant_ctx.tenant_id)  # type: ignore


@router.patch(
    "/current",
    response_model=TenantResponse,
    summary="Update current tenant settings",
    dependencies=[Depends(require_role("admin"))],
)
async def update_current_tenant(
    request: TenantUpdateRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session_with_tenant),
) -> TenantResponse:
    tenant_service = TenantService(session)
    return await tenant_service.update_tenant(  # type: ignore
        tenant_id=tenant_ctx.tenant_id,
        update_data=request.model_dump(exclude_unset=True),
    )


@router.post(
    "/{tenant_id}/switch",
    response_model=TokenResponse,
    summary="Switch tenant context (get new scoped token)",
)
async def switch_tenant(
    tenant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session_no_tenant),
) -> TokenResponse:
    auth_service = AuthService(session)
    access_token, refresh_token = await auth_service.create_tenant_scoped_token(
        user=current_user,
        tenant_id=tenant_id,
    )
    settings = get_settings()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# =============================================================================
# Membership Management
# =============================================================================


@router.get(
    "/current/members",
    response_model=list[TenantMemberResponse],
    summary="List all members of the current tenant",
    dependencies=[Depends(require_role("admin", "member", "read_only"))],
)
async def list_members(
    skip: int = 0,
    limit: int = 50,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session_with_tenant),
) -> list[TenantMemberResponse]:
    tenant_service = TenantService(session)
    memberships = await tenant_service.get_members(
        tenant_id=tenant_ctx.tenant_id,
        offset=skip,
        limit=limit,
    )

    # Map to schema explicitly since we need fields from the joined User model
    return [
        TenantMemberResponse(
            id=m.id,
            user_id=m.user_id,
            email=m.user.email,
            display_name=m.user.display_name,
            role=m.role,
            joined_at=m.joined_at,
        )
        for m in memberships
    ]


@router.patch(
    "/current/members/{user_id}/role",
    response_model=TenantMemberResponse,
    summary="Update a member's role",
    dependencies=[Depends(require_role("admin"))],
)
async def update_member_role(
    user_id: uuid.UUID,
    request: MemberRoleUpdateRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session_with_tenant),
) -> TenantMemberResponse:
    tenant_service = TenantService(session)
    m = await tenant_service.update_member_role(
        tenant_id=tenant_ctx.tenant_id,
        target_user_id=user_id,
        new_role=request.role,
        requesting_user_id=tenant_ctx.user_id,
    )

    # Refresh the relationship so user is loaded
    await session.refresh(m, ["user"])

    return TenantMemberResponse(
        id=m.id,
        user_id=m.user_id,
        email=m.user.email,
        display_name=m.user.display_name,
        role=m.role,
        joined_at=m.joined_at,
    )


@router.delete(
    "/current/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member from the tenant",
    dependencies=[Depends(require_role("admin", "member", "read_only"))],
)
async def remove_member(
    user_id: uuid.UUID,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session_with_tenant),
) -> None:
    tenant_service = TenantService(session)
    await tenant_service.remove_member(
        tenant_id=tenant_ctx.tenant_id,
        target_user_id=user_id,
        requesting_user_id=tenant_ctx.user_id,
    )


# =============================================================================
# Invitations
# =============================================================================


@router.post(
    "/current/invites",
    response_model=InviteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a new member to the tenant",
    dependencies=[Depends(require_role("admin"))],
)
async def create_invite(
    request: InviteCreateRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session_with_tenant),
) -> InviteResponse:
    tenant_service = TenantService(session)
    invite, _plaintext_token = await tenant_service.create_invite(
        tenant_id=tenant_ctx.tenant_id,
        email=request.email,
        role=request.role,
        invited_by=tenant_ctx.user_id,
    )

    # In production, dispatch invite email via Celery (token is never logged).
    from app.core.logging import get_logger

    logger = get_logger(__name__)
    logger.info(
        "invite_created",
        invite_id=str(invite.id),
        tenant_id=str(tenant_ctx.tenant_id),
        email=request.email,
    )

    return invite  # type: ignore


@router.post(
    "/invites/accept",
    response_model=TenantMemberResponse,
    summary="Accept a team invitation",
)
async def accept_invite(
    request: InviteAcceptRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session_no_tenant),
) -> TenantMemberResponse:
    tenant_service = TenantService(session)
    m = await tenant_service.accept_invite(
        token=request.token,
        user_id=current_user.id,
    )

    await session.refresh(m, ["user"])

    return TenantMemberResponse(
        id=m.id,
        user_id=m.user_id,
        email=m.user.email,
        display_name=m.user.display_name,
        role=m.role,
        joined_at=m.joined_at,
    )
