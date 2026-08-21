"""
AtlasOS SQLAlchemy Models Package.

Exports all SQLAlchemy models so that Alembic can easily discover them
via a single import in migrations/env.py: `from app.models import Base`.

Order matters here! We must import all modules containing models to ensure
they are attached to the DeclarativeBase metadata before Alembic reads it.
"""

from app.models.audit import AuditLog
from app.models.auth import ApiKey, OAuthAccount, Session, TeamInvite, TenantMembership
from app.models.base import Base
from app.models.evaluation import EvaluationMetric, EvaluationRun
from app.models.graph import EntityNode, EntityRelation
from app.models.memory import CompressionLog, ContradictionLog, EpisodicMemory, SemanticMemory
from app.models.notification import Notification

# Import all models to ensure they register with Base.metadata
from app.models.tenant import Tenant
from app.models.user import User
from app.models.webhook import Webhook, WebhookDelivery

__all__ = [
    "ApiKey",
    "AuditLog",
    "Base",
    "CompressionLog",
    "ContradictionLog",
    "EntityNode",
    "EntityRelation",
    "EpisodicMemory",
    "EvaluationMetric",
    "EvaluationRun",
    "Notification",
    "OAuthAccount",
    "SemanticMemory",
    "Session",
    "TeamInvite",
    "Tenant",
    "TenantMembership",
    "User",
    "Webhook",
    "WebhookDelivery",
]
