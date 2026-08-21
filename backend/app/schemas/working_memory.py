"""
AtlasOS Working Memory Schemas.
"""

from typing import Any

from pydantic import BaseModel, Field


class WorkingMemoryState(BaseModel):
    """Schema for updating working memory."""

    session_id: str = Field(..., description="The short-term session ID.")
    external_user_id: str = Field(...)
    updates: dict[str, Any] = Field(
        ...,
        description="Key-value pairs to set or update in the working memory.",
    )


class WorkingMemoryResponse(BaseModel):
    """Schema for returning working memory state."""

    session_id: str
    external_user_id: str
    state: dict[str, Any]
