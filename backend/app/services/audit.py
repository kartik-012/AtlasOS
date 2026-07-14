"""
AtlasOS Audit Service.

Provides a high-level interface for creating audit log entries.
Wraps the AuditLogRepository with convenience methods and ensures
request context (IP, user agent) is captured consistently.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.repositories.audit import AuditLogRepository

logger = get_logger(__name__)


class AuditService:
    """Service for recording immutable audit log entries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._audit_repo = AuditLogRepository(session)

    async def log_action(
        self,
        tenant_id: uuid.UUID,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        user_id: uuid.UUID | None = None,
        api_key_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_body: dict[str, Any] | None = None,
        response_status: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Create an audit log entry.

        Sanitizes the request_body to remove any potentially sensitive fields
        before storage.

        Args:
            tenant_id: Tenant UUID.
            action: Action identifier (e.g., 'api_key.create', 'memory.delete').
            resource_type: Type of resource (e.g., 'api_key', 'episodic_memory').
            resource_id: ID of the affected resource.
            user_id: User who performed the action.
            api_key_id: API key used for the action.
            ip_address: Client IP address.
            user_agent: Client User-Agent string.
            request_body: Request body (will be sanitized).
            response_status: HTTP response status code.
            metadata: Additional structured context.
        """
        # Sanitize request body — remove sensitive fields
        sanitized_body = _sanitize_request_body(request_body) if request_body else None

        await self._audit_repo.create_entry(
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            api_key_id=api_key_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_body=sanitized_body,
            response_status=response_status,
            metadata=metadata,
        )


def _sanitize_request_body(body: dict[str, Any]) -> dict[str, Any]:
    """
    Remove sensitive fields from a request body before audit logging.

    Sensitive field patterns:
      - password, secret, token, key (exact or suffix match)
      - Any field containing 'password', 'secret', 'token', 'key'

    Args:
        body: Raw request body dictionary.

    Returns:
        A new dictionary with sensitive values replaced by '[REDACTED]'.
    """
    sensitive_patterns = {"password", "secret", "token", "key", "hash", "credential"}
    sanitized: dict[str, Any] = {}

    for field_name, value in body.items():
        lower_name = field_name.lower()
        is_sensitive = any(pattern in lower_name for pattern in sensitive_patterns)
        if is_sensitive:
            sanitized[field_name] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[field_name] = _sanitize_request_body(value)
        else:
            sanitized[field_name] = value

    return sanitized
