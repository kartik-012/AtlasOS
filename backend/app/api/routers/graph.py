"""
AtlasOS Knowledge Graph API Router.

Endpoints for inspecting and querying the Knowledge Graph Entity Mesh.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.core.dependencies import (
    TenantContext,
    get_db_session_with_tenant,
    get_tenant_context,
    require_role,
)
from app.repositories.graph import EntityGraphRepository
from app.services.graph_service import EntityGraphService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])


class TripleExtractRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Input text to extract entity triples from.")
    external_user_id: str = Field(..., description="External user owning the extracted knowledge.")


class SubgraphQueryRequest(BaseModel):
    external_user_id: str = Field(...)
    entity_names: list[str] = Field(default_factory=list, description="Seed entity names to expand.")


@router.post(
    "/extract",
    summary="Extract entity triples and update graph",
    dependencies=[Depends(require_role("admin", "member"))],
)
async def extract_triples(
    request: TripleExtractRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session_with_tenant),
) -> dict[str, Any]:
    """Extract Subject-Predicate-Object triples from text and persist into Knowledge Graph Mesh."""
    service = EntityGraphService(session)
    triples = await service.extract_and_store_triples(
        tenant_id=tenant_ctx.tenant_id,
        external_user_id=request.external_user_id,
        text=request.text,
    )
    return {
        "triples": [{"subject": s, "predicate": p, "object": o} for s, p, o in triples],
        "count": len(triples),
    }


@router.get(
    "/subgraph/{external_user_id}",
    summary="Get Knowledge Graph subgraph for user",
    dependencies=[Depends(require_role("admin", "member", "read_only"))],
)
async def get_subgraph(
    external_user_id: str,
    entities: list[str] = Query(default=[]),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session_with_tenant),
) -> dict[str, Any]:
    """Retrieve nodes and directed edges for given entities or user context."""
    repo = EntityGraphRepository(session)
    if not entities:
        # Default seed entities
        entities = ["User"]

    subgraph = await repo.get_subgraph_for_entities(
        tenant_id=tenant_ctx.tenant_id,
        external_user_id=external_user_id,
        entity_names=entities,
    )
    return subgraph
