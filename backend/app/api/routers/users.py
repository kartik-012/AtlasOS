"""
AtlasOS Users API Router.

Endpoints for managing the current user's profile and checking their
tenant memberships.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user, get_db_session_no_tenant
from app.schemas.user import UserUpdateRequest, UserWithTenantsResponse
from app.services.user import UserService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserWithTenantsResponse,
    summary="Get current user profile and tenant memberships",
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session_no_tenant),
) -> UserWithTenantsResponse:
    user_service = UserService(session)
    tenants = await user_service.get_user_tenants(current_user.id)

    return UserWithTenantsResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url,
        is_active=current_user.is_active,
        email_verified=current_user.email_verified,
        last_login_at=current_user.last_login_at,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        tenants=tenants,
    )


@router.patch(
    "/me",
    response_model=UserWithTenantsResponse,
    summary="Update current user profile",
)
async def update_current_user_profile(
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session_no_tenant),
) -> UserWithTenantsResponse:
    user_service = UserService(session)
    updated_user = await user_service.update_profile(
        user_id=current_user.id,
        update_data=request.model_dump(exclude_unset=True),
    )

    tenants = await user_service.get_user_tenants(updated_user.id)

    return UserWithTenantsResponse(
        id=updated_user.id,
        email=updated_user.email,
        display_name=updated_user.display_name,
        avatar_url=updated_user.avatar_url,
        is_active=updated_user.is_active,
        email_verified=updated_user.email_verified,
        last_login_at=updated_user.last_login_at,
        created_at=updated_user.created_at,
        updated_at=updated_user.updated_at,
        tenants=tenants,
    )
