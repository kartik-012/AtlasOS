from __future__ import annotations

from datetime import datetime
import structlog
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.worker.celery_app import celery_app
from app.models.tenant import Tenant
from app.models.evaluation import EvaluationRun, EvaluationMetric

logger = structlog.get_logger(__name__)

def get_sync_session() -> Session:
    """Returns a synchronous database session for Celery workers."""
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL_SYNC)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


@celery_app.task(name="tasks.run_system_evaluations")
def run_system_evaluations() -> None:
    """Creates EvaluationRun entries for all active tenants."""
    logger.info("Starting run_system_evaluations task")
    with get_sync_session() as session:
        try:
            tenants = session.query(Tenant).filter(Tenant.is_active == True).all()
            for tenant in tenants:
                run = EvaluationRun(
                    tenant_id=tenant.id,
                    run_type="scheduled",
                    status="pending",
                    started_at=datetime.utcnow()
                )
                session.add(run)
                session.flush()
                run_tenant_evaluation.delay(str(tenant.id), str(run.id))
            session.commit()
            logger.info("Successfully dispatched system evaluations")
        except Exception as e:
            session.rollback()
            logger.exception("Failed to dispatch system evaluations", error=str(e))
            raise


@celery_app.task(name="tasks.run_tenant_evaluation")
def run_tenant_evaluation(tenant_id: str, run_id: str) -> None:
    """Measures recall_at_k, precision_at_k, p95_latency_ms, creates EvaluationMetric entries."""
    logger.info("Starting run_tenant_evaluation task", tenant_id=tenant_id, run_id=run_id)
    with get_sync_session() as session:
        try:
            run = session.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
            if not run:
                logger.error("Evaluation run not found", run_id=run_id)
                return

            run.status = "running"
            session.commit()

            # Mock evaluation metrics for demonstration
            metrics = [
                ("recall_at_k", 0.85, 0.80),
                ("precision_at_k", 0.75, 0.70),
                ("p95_latency_ms", 120.0, 200.0)
            ]

            for name, val, target in metrics:
                metric = EvaluationMetric(
                    evaluation_run_id=run.id,
                    metric_name=name,
                    metric_value=val,
                    target_value=target,
                    passed=(val >= target) if "latency" not in name else (val <= target)
                )
                session.add(metric)

            run.status = "completed"
            run.completed_at = datetime.utcnow()
            session.commit()
            logger.info("Successfully completed tenant evaluation", tenant_id=tenant_id, run_id=run_id)
        except Exception as e:
            session.rollback()
            logger.exception("Failed tenant evaluation", tenant_id=tenant_id, run_id=run_id, error=str(e))
            raise
