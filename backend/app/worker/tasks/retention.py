from __future__ import annotations

from datetime import datetime, timedelta
import structlog
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.worker.celery_app import celery_app
from app.models.tenant import Tenant
from app.models.memory import EpisodicMemory

logger = structlog.get_logger(__name__)

def get_sync_session() -> Session:
    """Returns a synchronous database session for Celery workers."""
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL_SYNC)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


@celery_app.task(name="tasks.sweep_expired_memories")
def sweep_expired_memories() -> None:
    """Deletes episodic memories older than tenant.retention_days for all tenants."""
    logger.info("Starting sweep_expired_memories task")
    with get_sync_session() as session:
        try:
            tenants = session.query(Tenant).all()
            for tenant in tenants:
                if tenant.retention_days:
                    cutoff_date = datetime.utcnow() - timedelta(days=tenant.retention_days)
                    deleted_count = session.query(EpisodicMemory).filter(
                        EpisodicMemory.tenant_id == tenant.id,
                        EpisodicMemory.created_at < cutoff_date
                    ).delete()
                    if deleted_count > 0:
                        logger.info("Swept expired memories", tenant_id=tenant.id, count=deleted_count)
            session.commit()
            logger.info("Successfully completed sweep_expired_memories task")
        except Exception as e:
            session.rollback()
            logger.exception("Failed to sweep expired memories", error=str(e))
            raise


@celery_app.task(name="tasks.decay_importance_scores")
def decay_importance_scores() -> None:
    """Reduces importance_score by a decay factor for memories not accessed recently."""
    logger.info("Starting decay_importance_scores task")
    decay_factor = 0.95
    with get_sync_session() as session:
        try:
            session.query(EpisodicMemory).update(
                {EpisodicMemory.importance_score: EpisodicMemory.importance_score * decay_factor},
                synchronize_session=False
            )
            session.commit()
            logger.info("Successfully completed decay_importance_scores task")
        except Exception as e:
            session.rollback()
            logger.exception("Failed to decay importance scores", error=str(e))
            raise
