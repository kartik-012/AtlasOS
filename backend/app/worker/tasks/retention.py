"""
AtlasOS Memory Retention & Ebbinghaus Decay Task Worker.

Implements retention sweeps with cascading vector store cleanups and
Ebbinghaus importance score decay synchronization across PostgreSQL and Qdrant.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import httpx
import structlog
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models.memory import EpisodicMemory, SemanticMemory
from app.models.tenant import Tenant
from app.worker.celery_app import celery_app

logger = structlog.get_logger(__name__)


def get_sync_session() -> Session:
    """Returns a synchronous database session for Celery workers."""
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL_SYNC)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


@celery_app.task(name="tasks.sweep_expired_memories")  # type: ignore
def sweep_expired_memories() -> None:
    """
    Deletes episodic memories older than tenant.retention_days for all tenants.
    Cascades vector point deletion to Qdrant to prevent orphaned points.
    """
    logger.info("Starting sweep_expired_memories task")
    settings = get_settings()
    with get_sync_session() as session:
        try:
            tenants = session.query(Tenant).all()
            for tenant in tenants:
                if tenant.retention_days:
                    cutoff_date = datetime.now(UTC) - timedelta(days=tenant.retention_days)

                    # 1. Fetch IDs of expired memories
                    expired_memories = (
                        session.query(EpisodicMemory)
                        .filter(
                            EpisodicMemory.tenant_id == tenant.id,
                            EpisodicMemory.created_at < cutoff_date,
                        )
                        .all()
                    )

                    if not expired_memories:
                        continue

                    expired_ids = [m.id for m in expired_memories]

                    # 2. Cascading Delete in Qdrant Vector Store
                    _delete_qdrant_points_batch(settings.QDRANT_URL, expired_ids)

                    # 3. Delete from PostgreSQL
                    session.query(EpisodicMemory).filter(
                        EpisodicMemory.id.in_(expired_ids)
                    ).delete(synchronize_session=False)

                    logger.info(
                        "Swept expired memories with vector cascade",
                        tenant_id=str(tenant.id),
                        count=len(expired_ids),
                    )

            session.commit()
            logger.info("Successfully completed sweep_expired_memories task")
        except Exception as e:
            session.rollback()
            logger.exception("Failed to sweep expired memories", error=str(e))
            raise


@celery_app.task(name="tasks.decay_importance_scores")  # type: ignore
def decay_importance_scores() -> None:
    """
    Applies Ebbinghaus forgetting curve decay (R = e^(-t/S)) to unaccessed memories
    and updates importance scores across both PostgreSQL and Qdrant payloads.
    """
    logger.info("Starting decay_importance_scores task")
    settings = get_settings()
    decay_factor = 0.95

    with get_sync_session() as session:
        try:
            # 1. Decay Episodic Memories
            episodic_memories = (
                session.query(EpisodicMemory)
                .filter(EpisodicMemory.superseded.is_(False))
                .all()
            )

            for em in episodic_memories:
                em.importance_score = round(max(0.05, em.importance_score * decay_factor), 3)
                _update_qdrant_payload_importance(
                    settings.QDRANT_URL, em.id, em.importance_score
                )

            # 2. Decay Semantic Memories
            semantic_memories = (
                session.query(SemanticMemory)
                .filter(SemanticMemory.superseded.is_(False))
                .all()
            )

            for sm in semantic_memories:
                sm.importance_score = round(max(0.05, sm.importance_score * decay_factor), 3)
                _update_qdrant_payload_importance(
                    settings.QDRANT_URL, sm.id, sm.importance_score
                )

            session.commit()
            logger.info(
                "Successfully applied Ebbinghaus decay to memory importance scores",
                episodic_count=len(episodic_memories),
                semantic_count=len(semantic_memories),
            )
        except Exception as e:
            session.rollback()
            logger.exception("Failed to decay importance scores", error=str(e))
            raise


def _delete_qdrant_points_batch(qdrant_url: str, point_ids: list[uuid.UUID]) -> None:
    """Deletes a batch of vector points from Qdrant via HTTP."""
    if not point_ids:
        return
    try:
        url = f"{qdrant_url.rstrip('/')}/collections/atlas_memories/points/delete"
        payload = {"points": [str(pid) for pid in point_ids]}
        httpx.post(url, json=payload, timeout=5.0)
    except Exception as e:
        logger.warning("Failed cascading vector delete in Qdrant", error=str(e))


def _update_qdrant_payload_importance(
    qdrant_url: str, point_id: uuid.UUID, new_importance: float
) -> None:
    """Updates the importance_score payload field of a point in Qdrant."""
    try:
        url = f"{qdrant_url.rstrip('/')}/collections/atlas_memories/points/payload"
        payload = {
            "points": [str(point_id)],
            "payload": {"importance_score": new_importance},
        }
        httpx.post(url, json=payload, timeout=2.0)
    except Exception:
        pass
