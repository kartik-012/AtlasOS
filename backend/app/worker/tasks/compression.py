from __future__ import annotations

import structlog
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.worker.celery_app import celery_app
from app.models.tenant import Tenant
from app.models.memory import EpisodicMemory, SemanticMemory, CompressionLog

logger = structlog.get_logger(__name__)

def get_sync_session() -> Session:
    """Returns a synchronous database session for Celery workers."""
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL_SYNC)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


@celery_app.task(name="tasks.compress_all_tenants_memories")
def compress_all_tenants_memories() -> None:
    """Iterates all active tenants and triggers memory compression for each."""
    logger.info("Starting compress_all_tenants_memories task")
    with get_sync_session() as session:
        try:
            tenants = session.query(Tenant).all()
            for tenant in tenants:
                compress_tenant_memories.delay(str(tenant.id))
            logger.info("Successfully dispatched compression tasks for all tenants", count=len(tenants))
        except Exception as e:
            logger.exception("Failed to dispatch compression tasks", error=str(e))
            raise


@celery_app.task(name="tasks.compress_tenant_memories")
def compress_tenant_memories(tenant_id: str) -> None:
    """Finds groups of similar episodic memories, summarizes them, and creates a SemanticMemory + CompressionLog entry."""
    logger.info("Starting compress_tenant_memories task", tenant_id=tenant_id)
    with get_sync_session() as session:
        try:
            # Placeholder for querying Qdrant, finding clusters, summarizing using LLM,
            # and storing SemanticMemory + CompressionLog.
            logger.info("Compression completed", tenant_id=tenant_id)
        except Exception as e:
            logger.exception("Failed to compress tenant memories", tenant_id=tenant_id, error=str(e))
            raise
