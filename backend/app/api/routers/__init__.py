"""
AtlasOS API Routers Package.
"""

from app.api.routers import (
    auth,
    tenants,
    users,
    memories,
    working_memory,
    webhooks,
    contradictions,
    evaluations,
    audit,
    system,
    ws,
)

__all__ = [
    "auth",
    "tenants",
    "users",
    "memories",
    "working_memory",
    "webhooks",
    "contradictions",
    "evaluations",
    "audit",
    "system",
    "ws",
]
