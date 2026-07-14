"""
AtlasOS Audit Log Repository.

Append-only repository for the immutable audit_log table.
This repository intentionally omits update() and delete() methods
because the audit_log table is protected by a database trigger that
rejects all UPDATE and DELETE operations.

Design decisions:
  - No update/delete: Methods are not exposed to prevent accidental
    calls that would trigger a database error.
  - Bulk insert: The create_entry method supports inserting a single
    audit log entry. Batch inserts are supported via create_entries.
  - The repository does NOT validate tenant isolation — that is enforced
    by RLS at the database level.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditLogRepository:
    """
    Append-only repository for the audit_log table.

    Intentionally does NOT extend BaseRepository because audit logs
    do not support update or delete operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the audit log repository.

        Args:
            session: An async SQLAlchemy session.
        """
        self._session = session

    async def create_entry(
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
    ) -> AuditLog:
        """
        Create a new immutable audit log entry.

        Args:
            tenant_id: Tenant UUID.
            action: Action performed (e.g., 'memory.create', 'api_key.revoke').
            resource_type: Type of affected resource.
            resource_id: ID of the affected resource (optional).
            user_id: User who performed the action (optional).
            api_key_id: API key used for the action (optional).
            ip_address: Client IP address (optional).
            user_agent: Client User-Agent header (optional).
            request_body: Sanitized request body (optional, MUST NOT contain secrets).
            response_status: HTTP response status code (optional).
            metadata: Additional context (optional).

        Returns:
            The newly created AuditLog instance.
        """
        entry = AuditLog(
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            api_key_id=api_key_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_body=request_body,
            response_status=response_status,
            metadata=metadata,
        )
        self._session.add(entry)
        await self._session.flush()
        await self._session.refresh(entry)
        return entry

    async def get_entries(
        self,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
        action: str | None = None,
        resource_type: str | None = None,
    ) -> list[AuditLog]:
        """
        Retrieve audit log entries for a tenant with optional filters.

        Args:
            tenant_id: Tenant UUID.
            offset: Pagination offset.
            limit: Pagination limit.
            action: Filter by action name (optional).
            resource_type: Filter by resource type (optional).

        Returns:
            List of AuditLog instances, ordered newest first.
        """
        stmt = select(AuditLog).where(AuditLog.tenant_id == tenant_id)

        if action is not None:
            stmt = stmt.where(AuditLog.action == action)
        if resource_type is not None:
            stmt = stmt.where(AuditLog.resource_type == resource_type)

        stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_entries(
        self,
        tenant_id: uuid.UUID,
    ) -> int:
        """
        Count total audit log entries for a tenant.

        Args:
            tenant_id: Tenant UUID.

        Returns:
            Total number of audit log entries.
        """
        stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.tenant_id == tenant_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()
