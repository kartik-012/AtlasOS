"""
AtlasOS API Routers Package.
"""

from app.api.routers import (
    audit,
    auth,
    contradictions,
    evaluations,
    graph,
    memories,
    system,
    tenants,
    users,
    webhooks,
    working_memory,
    ws,
)

__all__ = [
    "audit",
    "auth",
    "contradictions",
    "evaluations",
    "graph",
    "memories",
    "system",
    "tenants",
    "users",
    "webhooks",
    "working_memory",
    "ws",
]
