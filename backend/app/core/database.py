"""
AtlasOS Database Engine & Session Management.

Provides async (for application) and sync (for Alembic migrations) database
engines, session factories, and a FastAPI dependency for request-scoped
database sessions with Row-Level Security (RLS) tenant context.

Architecture decisions:
  - Async engine (asyncpg): Used by the FastAPI application for non-blocking
    database access. Enables high concurrency under I/O-bound workloads.
  - Sync engine (psycopg2): Used exclusively by Alembic for migrations.
    Alembic does not support async operations natively.
  - Connection pooling: pool_size=20 with max_overflow=10 allows up to 30
    concurrent connections. pool_pre_ping detects stale connections.
    pool_recycle=3600 prevents connections from being held indefinitely.

RLS integration:
  Every request-scoped session sets the PostgreSQL session variable
  `app.current_tenant_id` via SET LOCAL. This variable is referenced by
  RLS policies on all tenant-scoped tables, ensuring that queries
  automatically filter to the authenticated tenant's data.

  SET LOCAL is scoped to the current transaction, so it does not leak
  across requests even with connection pooling.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.engine import Engine, create_engine

from app.core.config import get_settings


def _create_async_engine() -> AsyncEngine:
    """
    Create the async SQLAlchemy engine for the FastAPI application.

    Pool configuration rationale:
      - pool_size=20: Baseline connections kept open. Matches typical
        concurrent request volume for a single backend instance.
      - max_overflow=10: Burst capacity above pool_size. Total max = 30.
      - pool_pre_ping=True: Validates connections before use. Prevents
        errors from stale connections after database restarts.
      - pool_recycle=3600: Recycles connections after 1 hour to prevent
        issues with database-side connection timeouts.
    """
    settings = get_settings()
    return create_async_engine(
        settings.DATABASE_URL,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=settings.is_development,
        future=True,
    )


def _create_sync_engine() -> Engine:
    """
    Create the sync SQLAlchemy engine for Alembic migrations.

    Uses psycopg2 driver. Only used by migration tooling, never by
    the running application. Minimal pool configuration since migrations
    are single-threaded sequential operations.
    """
    settings = get_settings()
    return create_engine(
        settings.DATABASE_URL_SYNC,
        pool_pre_ping=True,
        echo=settings.is_development,
        future=True,
    )


# Module-level engine instances.
# These are created once at import time and reused across the application.
async_engine: AsyncEngine = _create_async_engine()
sync_engine: Engine = _create_sync_engine()

# Async session factory bound to the async engine.
# expire_on_commit=False: Prevents lazy-load errors after commit.
# This is necessary because SQLAlchemy would otherwise try to refresh
# attributes from the database after commit, which requires an active
# connection and can cause unexpected I/O in async contexts.
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session(
    tenant_id: uuid.UUID | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a request-scoped async database session.

    This dependency:
      1. Creates a new AsyncSession from the factory.
      2. If a tenant_id is provided, sets the PostgreSQL session variable
         `app.current_tenant_id` for RLS policy enforcement.
      3. Yields the session for use in the request handler.
      4. Commits the transaction on success.
      5. Rolls back on any exception.
      6. Always closes the session.

    Note on tenant_id:
      In Phase 2, the tenant_id will be extracted from the authenticated
      user's JWT token or API key by an auth dependency. The auth
      dependency will be composed with this dependency to form a
      tenant-scoped session dependency.

    Args:
        tenant_id: The UUID of the tenant to scope the session to.
                   If None, no RLS context is set (used for operations
                   that are not tenant-scoped, e.g., user lookup by email).

    Yields:
        AsyncSession: A request-scoped database session.

    Raises:
        Exception: Re-raises any exception after rolling back the session.
    """
    session = async_session_factory()
    try:
        if tenant_id is not None:
            # SET LOCAL scopes the setting to the current transaction only.
            # This prevents tenant_id leakage across requests when
            # connections are reused from the pool.
            await session.execute(
                text("SET LOCAL app.current_tenant_id = :tenant_id"),
                {"tenant_id": str(tenant_id)},
            )
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
