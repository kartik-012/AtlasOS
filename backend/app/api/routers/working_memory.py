"""
AtlasOS Working Memory API Router.

Endpoints for managing short-term ephemeral state in Redis.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.dependencies import (
    TenantContext,
    get_tenant_context,
    require_role,
)
from app.repositories.working_memory import WorkingMemoryRepository
from app.schemas.working_memory import WorkingMemoryResponse, WorkingMemoryState

router = APIRouter(prefix="/working-memory", tags=["Working Memory"])


def get_wm_repo() -> WorkingMemoryRepository:
    return WorkingMemoryRepository()


@router.get(
    "/{external_user_id}/{session_id}",
    response_model=WorkingMemoryResponse,
    summary="Get current working memory state",
    dependencies=[Depends(require_role("admin", "member", "read_only"))],
)
async def get_working_memory(
    external_user_id: str,
    session_id: str,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    repo: WorkingMemoryRepository = Depends(get_wm_repo),
) -> WorkingMemoryResponse:
    state = await repo.get_state(
        tenant_id=tenant_ctx.tenant_id,
        external_user_id=external_user_id,
        session_id=session_id,
    )
    return WorkingMemoryResponse(
        session_id=session_id,
        external_user_id=external_user_id,
        state=state,
    )


@router.post(
    "/",
    response_model=WorkingMemoryResponse,
    summary="Update working memory state",
    dependencies=[Depends(require_role("admin", "member"))],
)
async def update_working_memory(
    request: WorkingMemoryState,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    repo: WorkingMemoryRepository = Depends(get_wm_repo),
) -> WorkingMemoryResponse:
    await repo.update_state(
        tenant_id=tenant_ctx.tenant_id,
        external_user_id=request.external_user_id,
        session_id=request.session_id,
        updates=request.updates,
    )
    state = await repo.get_state(
        tenant_id=tenant_ctx.tenant_id,
        external_user_id=request.external_user_id,
        session_id=request.session_id,
    )
    return WorkingMemoryResponse(
        session_id=request.session_id,
        external_user_id=request.external_user_id,
        state=state,
    )


@router.delete(
    "/{external_user_id}/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear working memory state",
    dependencies=[Depends(require_role("admin", "member"))],
)
async def clear_working_memory(
    external_user_id: str,
    session_id: str,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    repo: WorkingMemoryRepository = Depends(get_wm_repo),
) -> None:
    await repo.delete_state(
        tenant_id=tenant_ctx.tenant_id,
        external_user_id=external_user_id,
        session_id=session_id,
    )
