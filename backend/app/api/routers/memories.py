"""
AtlasOS Memory API Router.

Endpoints for writing and searching episodic and semantic memories.
Protected by API key permissions or JWT roles.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    TenantContext,
    get_db_session_with_tenant,
    get_tenant_context,
    require_permission,
    require_role,
)
from app.providers.embeddings import HTTPEmbeddingProvider
from app.providers.nli import HTTPNLIProvider
from app.repositories.vector import VectorRepository
from app.schemas.memory import (
    EpisodicMemoryCreate,
    MemorySearchQuery,
    MemorySearchResponse,
    MemoryWriteResponse,
    SemanticMemoryCreate,
)
from app.services.memory_read import MemoryReadService
from app.services.memory_write import MemoryWriteService

router = APIRouter(prefix="/memories", tags=["Memory"])


def get_write_service(
    session: AsyncSession = Depends(get_db_session_with_tenant),
) -> MemoryWriteService:
    """Dependency provider for MemoryWriteService."""
    embedding_provider = HTTPEmbeddingProvider()
    nli_provider = HTTPNLIProvider()
    vector_repo = VectorRepository()
    return MemoryWriteService(
        session=session,
        embedding_provider=embedding_provider,
        nli_provider=nli_provider,
        vector_repo=vector_repo,
    )


def get_read_service(
    session: AsyncSession = Depends(get_db_session_with_tenant),
) -> MemoryReadService:
    """Dependency provider for MemoryReadService."""
    embedding_provider = HTTPEmbeddingProvider()
    vector_repo = VectorRepository()
    return MemoryReadService(
        session=session,
        embedding_provider=embedding_provider,
        vector_repo=vector_repo,
    )


@router.post(
    "/episodic",
    response_model=MemoryWriteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Write a new episodic memory",
    # Require either 'admin/member' console role, or 'memory:write' API key permission
    dependencies=[Depends(require_role("admin", "member"))],
)
async def write_episodic_memory(
    request: EpisodicMemoryCreate,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    write_service: MemoryWriteService = Depends(get_write_service),
) -> MemoryWriteResponse:
    memory = await write_service.write_episodic(
        tenant_id=tenant_ctx.tenant_id,
        external_user_id=request.external_user_id,
        content=request.content,
        metadata=request.metadata,
    )
    return MemoryWriteResponse(
        id=memory.id,
        external_user_id=memory.external_user_id,
        memory_type="episodic",
        content=memory.content,
        importance_score=memory.importance_score,
        created_at=memory.created_at,
    )


@router.post(
    "/semantic",
    response_model=MemoryWriteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Write a new semantic memory (fact)",
    dependencies=[Depends(require_role("admin", "member"))],
)
async def write_semantic_memory(
    request: SemanticMemoryCreate,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    write_service: MemoryWriteService = Depends(get_write_service),
) -> MemoryWriteResponse:
    memory, has_contradiction, log_id = await write_service.write_semantic(
        tenant_id=tenant_ctx.tenant_id,
        external_user_id=request.external_user_id,
        content=request.content,
        source_episodic_id=request.source_episodic_id,
        metadata=request.metadata,
    )
    return MemoryWriteResponse(
        id=memory.id,
        external_user_id=memory.external_user_id,
        memory_type="semantic",
        content=memory.content,
        importance_score=memory.importance_score,
        contradiction_detected=has_contradiction,
        contradiction_log_id=log_id,
        created_at=memory.created_at,
    )


@router.post(
    "/search",
    response_model=MemorySearchResponse,
    summary="Search episodic and semantic memories",
    # Anyone with read access can search
    dependencies=[Depends(require_role("admin", "member", "read_only"))],
)
async def search_memories(
    request: MemorySearchQuery,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    read_service: MemoryReadService = Depends(get_read_service),
) -> MemorySearchResponse:
    return await read_service.search(
        tenant_id=tenant_ctx.tenant_id,
        external_user_id=request.external_user_id,
        query=request.query,
        memory_type=request.memory_type,
        limit=request.limit,
        score_threshold=request.score_threshold,
    )
