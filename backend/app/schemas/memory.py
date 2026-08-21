"""
AtlasOS Memory Schemas.

Pydantic schemas for the memory pipelines: episodic writes,
semantic writes, retrieval queries, and contradiction resolution.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import AtlasBaseSchema

# =============================================================================
# Write Payloads
# =============================================================================


class EpisodicMemoryCreate(BaseModel):
    """Payload for writing a new episodic memory."""

    external_user_id: str = Field(
        ...,
        description="ID of the user this memory belongs to from the external application.",
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The raw text of the memory/experience.",
    )
    meta_data: dict[str, Any] = Field(
        default_factory=dict,
        alias="metadata",
        description="Optional structured metadata (e.g., location, emotion, source).",
    )


class SemanticMemoryCreate(BaseModel):
    """Payload for writing a new semantic memory (fact)."""

    external_user_id: str = Field(...)
    content: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The consolidated fact.",
    )
    source_episodic_id: uuid.UUID | None = Field(
        None,
        description="Optional ID of the episodic memory this fact was derived from.",
    )
    meta_data: dict[str, Any] = Field(default_factory=dict, alias="metadata")


# =============================================================================
# Read Queries
# =============================================================================


class MemorySearchQuery(BaseModel):
    """Query payload for the retrieval engine."""

    external_user_id: str = Field(...)
    query: str = Field(
        ...,
        description="Natural language query to search for.",
    )
    memory_type: str | None = Field(
        None,
        description="Optional filter: 'episodic' or 'semantic'. If None, searches both.",
    )
    limit: int = Field(default=10, ge=1, le=100)
    score_threshold: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Optional minimum cosine similarity threshold.",
    )


# =============================================================================
# Responses
# =============================================================================


class MemoryWriteResponse(AtlasBaseSchema):
    """Response returned after a memory is successfully written."""

    id: uuid.UUID
    external_user_id: str
    memory_type: str
    content: str
    importance_score: float
    contradiction_detected: bool = False
    contradiction_log_id: uuid.UUID | None = None
    created_at: datetime


class ScoredMemoryResult(AtlasBaseSchema):
    """A single memory returned from a search with its composite score."""

    id: uuid.UUID
    memory_type: str
    content: str
    meta_data: dict[str, Any] = Field(alias="metadata")
    importance_score: float
    similarity_score: float
    composite_score: float
    created_at: datetime


class MemorySearchResponse(AtlasBaseSchema):
    """Response payload for a memory search query."""

    results: list[ScoredMemoryResult]
    query_time_ms: float
    knowledge_graph: dict[str, Any] | None = None


# =============================================================================
# Contradiction Resolution
# =============================================================================


class ContradictionResolution(BaseModel):
    """Payload for manually resolving a contradiction."""

    log_id: uuid.UUID
    resolution_choice: str = Field(
        ...,
        description="Must be 'keep_new', 'keep_existing', or 'keep_both'.",
    )
