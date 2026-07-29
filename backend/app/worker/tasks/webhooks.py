from __future__ import annotations

import json
import hmac
import hashlib
from datetime import datetime
import requests
import structlog
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.worker.celery_app import celery_app
from app.models.webhook import Webhook, WebhookDelivery

logger = structlog.get_logger(__name__)

def get_sync_session() -> Session:
    """Returns a synchronous database session for Celery workers."""
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL_SYNC)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


@celery_app.task(bind=True, max_retries=5, default_retry_delay=30, name="tasks.deliver_webhook")
def deliver_webhook(self, webhook_id: str, event_type: str, payload: dict) -> None:
    """Sends HTTP POST to webhook URL with HMAC signature, creates WebhookDelivery entry."""
    logger.info("Starting deliver_webhook task", webhook_id=webhook_id, event_type=event_type, attempt=self.request.retries)
    with get_sync_session() as session:
        try:
            webhook = session.query(Webhook).filter(Webhook.id == webhook_id).first()
            if not webhook or not webhook.is_active:
                logger.warning("Webhook not found or inactive", webhook_id=webhook_id)
                return

            delivery = WebhookDelivery(
                webhook_id=webhook.id,
                event_type=event_type,
                payload=payload,
                status="pending",
                attempt_number=self.request.retries + 1
            )
            session.add(delivery)
            session.flush()

            payload_bytes = json.dumps(payload).encode("utf-8")
            signature = hmac.new(webhook.secret_hash.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
            headers = {
                "Content-Type": "application/json",
                "X-Atlas-Signature": signature,
                "X-Atlas-Event": event_type,
            }

            try:
                response = requests.post(webhook.url, data=payload_bytes, headers=headers, timeout=10)
                delivery.response_status = response.status_code
                delivery.response_body = response.text
                
                if response.ok:
                    delivery.status = "delivered"
                    webhook.last_triggered_at = datetime.utcnow()
                    webhook.failure_count = 0
                else:
                    delivery.status = "failed"
                    delivery.error_message = f"HTTP Error {response.status_code}"
                    raise Exception(f"HTTP Error {response.status_code}")
                
            except Exception as req_e:
                delivery.status = "failed"
                delivery.error_message = str(req_e)
                webhook.failure_count = (webhook.failure_count or 0) + 1
                webhook.last_failure_at = datetime.utcnow()
                session.commit()
                logger.warning("Webhook delivery failed, scheduling retry", webhook_id=webhook_id, error=str(req_e))
                raise self.retry(exc=req_e)

            delivery.delivered_at = datetime.utcnow()
            session.commit()
            logger.info("Successfully delivered webhook", webhook_id=webhook_id, delivery_id=delivery.id)
            
        except Exception as e:
            if not isinstance(e, self.retry):
                session.rollback()
                logger.exception("Failed to process webhook delivery", webhook_id=webhook_id, error=str(e))
                raise


@celery_app.task(name="tasks.dispatch_event")
def dispatch_event(tenant_id: str, event_type: str, payload: dict) -> None:
    """Finds all active webhooks for the tenant subscribed to this event_type and dispatches deliver_webhook."""
    logger.info("Starting dispatch_event task", tenant_id=tenant_id, event_type=event_type)
    with get_sync_session() as session:
        try:
            webhooks = session.query(Webhook).filter(
                Webhook.tenant_id == tenant_id,
                Webhook.is_active == True
            ).all()
            
            dispatched = 0
            for webhook in webhooks:
                if webhook.events and event_type in webhook.events:
                    deliver_webhook.delay(str(webhook.id), event_type, payload)
                    dispatched += 1
            
            logger.info("Successfully dispatched events to webhooks", count=dispatched)
        except Exception as e:
            logger.exception("Failed to dispatch event", tenant_id=tenant_id, error=str(e))
            raise
