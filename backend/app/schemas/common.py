"""
AtlasOS Common Schema Utilities.

Provides base schema classes and reusable field types used across
all domain-specific schemas. Enforces consistent serialization
behavior and naming conventions.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AtlasBaseSchema(BaseModel):
    """
    Base schema for all AtlasOS Pydantic models.

    Provides:
      - from_attributes=True: Enables direct ORM model → schema conversion
        via `SchemaClass.model_validate(orm_instance)`.
      - populate_by_name=True: Allows field population by alias or Python name.
      - str_strip_whitespace=True: Strips leading/trailing whitespace from
        all string fields, preventing accidental whitespace in user input.
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class TimestampSchema(AtlasBaseSchema):
    """Mixin for schemas that include created_at/updated_at timestamps."""

    created_at: datetime
    updated_at: datetime


class PaginatedResponse(AtlasBaseSchema):
    """
    Standard paginated response envelope.

    Used by all list endpoints to provide consistent pagination metadata.
    """

    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorResponse(AtlasBaseSchema):
    """Standard error response matching the AtlasOSError.to_dict() format."""

    error: ErrorDetail
    status_code: int


class ErrorDetail(AtlasBaseSchema):
    """Error detail nested within ErrorResponse."""

    code: str
    message: str
    detail: dict[str, Any] | None = None
