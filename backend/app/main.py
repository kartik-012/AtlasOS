"""
AtlasOS FastAPI Application Entry Point.

Defines the application factory and lifespan management for the FastAPI
backend. The application factory pattern enables:
  - Testability: Tests can create isolated app instances with custom config.
  - Lazy initialization: Database engines and Redis connections are created
    only when the app starts, not at import time.
  - Clean shutdown: Resources are released gracefully on shutdown.

Phase 1 scope:
  - Health check endpoint for container orchestration.
  - Lifespan management for database engine.
  - Structured logging initialization.

Future phases will add:
  - Phase 2: Auth middleware, CORS, CSRF, rate limiting, API routes.
  - Phase 3: Memory pipeline endpoints.
  - Phase 4: Celery task triggers.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Any

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from app import __version__
from app.core.config import get_settings
from app.core.database import async_engine
from app.core.logging import get_logger, setup_logging


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Manage application lifecycle events.

    Startup:
      - Initialize structured logging.
      - Log application start with version and environment.
      - Verify database engine connectivity (pool warmup).

    Shutdown:
      - Dispose the async database engine (closes all pooled connections).
      - Log clean shutdown confirmation.

    The lifespan context manager replaces the deprecated @app.on_event()
    hooks, providing deterministic startup/shutdown ordering.
    """
    # --- Startup ---
    setup_logging()
    settings = get_settings()
    logger.info(
        "application_starting",
        version=__version__,
        environment=settings.ENVIRONMENT,
        database_host=settings.DATABASE_URL.split("@")[-1].split("/")[0]
        if "@" in settings.DATABASE_URL
        else "unknown",
    )

    yield

    # --- Shutdown ---
    logger.info("application_shutting_down")
    await async_engine.dispose()
    logger.info("database_engine_disposed")


def create_app() -> FastAPI:
    """
    Application factory for the AtlasOS FastAPI backend.

    Creates and configures a FastAPI application instance with:
      - Metadata (title, version, description) for OpenAPI docs.
      - ORJSONResponse as default response class for faster serialization.
      - Lifespan context manager for startup/shutdown.
      - Health check endpoint.

    Returns:
        FastAPI: Configured application instance.
    """
    settings = get_settings()

    application = FastAPI(
        title="AtlasOS API",
        description=(
            "AtlasOS — AI Memory Operating System. "
            "Provides hierarchical memory management (working, episodic, semantic) "
            "for AI agents with built-in contradiction detection, compression, "
            "and evaluation pipelines."
        ),
        version=__version__,
        lifespan=lifespan,
        default_response_class=ORJSONResponse,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
    )

    # Register routes
    _register_health_routes(application)

    return application


def _register_health_routes(application: FastAPI) -> None:
    """
    Register system health check endpoints.

    The /health endpoint is used by:
      - Docker Compose healthchecks to determine container readiness.
      - Load balancers to route traffic only to healthy instances.
      - Monitoring systems to track service availability.

    It intentionally does NOT check downstream dependencies (database, Redis)
    because a failing dependency should not cause the API container itself
    to be marked unhealthy and restarted. Dependency health is monitored
    separately.
    """

    @application.get(
        "/health",
        tags=["System"],
        summary="Health Check",
        description="Returns the current health status and version of the API.",
        response_model=dict[str, str],
    )
    async def health_check() -> dict[str, str]:
        """
        Health check endpoint.

        Returns:
            A dictionary with status and version information.
        """
        return {
            "status": "healthy",
            "version": __version__,
            "service": "atlasos-api",
        }


# Create the default application instance.
# This is what uvicorn imports: `uvicorn app.main:app`
app: FastAPI = create_app()
