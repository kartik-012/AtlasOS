"""
AtlasOS FastAPI Application Entry Point.

Defines the application factory and lifespan management for the FastAPI
backend. The application factory pattern enables:
  - Testability: Tests can create isolated app instances with custom config.
  - Lazy initialization: Database engines and Redis connections are created
    only when the app starts, not at import time.
  - Clean shutdown: Resources are released gracefully on shutdown.

Phase 2 additions:
  - Global Exception Handlers (AtlasOSError)
  - CORS Middleware
  - Rate Limiting Middleware
  - Core API Routers (Auth, Tenants, Users)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app import __version__
from app.core.config import get_settings
from app.core.database import async_engine
from app.core.logging import get_logger, setup_logging

# Middlewares & Handlers
from app.api.middlewares import RateLimitMiddleware, register_exception_handlers

# Routers
from app.api.routers import auth, tenants, users

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Manage application lifecycle events.

    Startup:
      - Initialize structured logging.
      - Log application start with version and environment.

    Shutdown:
      - Dispose the async database engine.
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
      - Metadata for OpenAPI docs.
      - ORJSONResponse as default.
      - Middlewares (CORS, Rate Limiting).
      - Exception Handlers.
      - API Routers.
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

    # Register Exception Handlers
    register_exception_handlers(application)

    # Configure CORS
    origins = [
        "http://localhost:3000",
        "https://localhost:3000",
    ]
    if not settings.is_development:
        origins = [] # Add production origins here

    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    )

    # Configure Rate Limiting Middleware
    application.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=600 if settings.is_development else 60,
    )

    # Register Routers
    api_prefix = "/api/v1"
    application.include_router(auth.router, prefix=api_prefix)
    application.include_router(tenants.router, prefix=api_prefix)
    application.include_router(users.router, prefix=api_prefix)

    # Register Health Route
    _register_health_routes(application)

    return application


def _register_health_routes(application: FastAPI) -> None:
    """
    Register system health check endpoints.
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
        """
        return {
            "status": "healthy",
            "version": __version__,
            "service": "atlasos-api",
        }


# Create the default application instance.
# This is what uvicorn imports: `uvicorn app.main:app`
app: FastAPI = create_app()
