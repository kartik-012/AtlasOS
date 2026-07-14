"""
AtlasOS Structured Logging Configuration.

Configures structlog for consistent, machine-parseable log output across
the entire backend application and Celery workers.

Design decisions:
  - JSON output in production: Enables log aggregation tools (ELK, Datadog,
    CloudWatch) to parse and index log fields automatically.
  - Console output in development: Human-readable colored output for local
    debugging without needing a log viewer.
  - Bound context (service, environment): Every log line includes the
    service name and environment, enabling filtering in multi-service
    deployments.
  - ISO 8601 timestamps: Unambiguous, timezone-aware, sortable.
  - CallsiteParameterAdder: Adds filename, function name, and line number
    to every log entry for traceability.

Usage:
    from app.core.logging import get_logger

    logger = get_logger(__name__)
    logger.info("memory_created", tenant_id=str(tenant_id), memory_type="episodic")
"""

from __future__ import annotations

import logging
import sys

import structlog

from app.core.config import get_settings


def setup_logging() -> None:
    """
    Configure structlog and stdlib logging for the application.

    Must be called once at application startup (in the FastAPI lifespan
    or Celery worker initialization).

    Configures:
      - structlog processors for context binding, timestamps, and formatting.
      - stdlib logging to route through structlog for unified output.
      - Log level from application settings.
    """
    settings = get_settings()

    # Determine log level from settings
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Shared processors applied to every log event
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.CallsiteParameterAdder(
            [
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ],
        ),
    ]

    if settings.is_production:
        # Production: JSON output for log aggregation pipelines
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: colored, human-readable console output
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure the stdlib root logger to use structlog's formatter.
    # This ensures that third-party libraries using stdlib logging
    # (e.g., SQLAlchemy, uvicorn) also produce structured output.
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Suppress overly verbose loggers from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.is_development else logging.WARNING,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Create a bound logger with service context.

    Every logger created through this factory automatically includes:
      - service: "atlasos" (identifies the service in multi-service deployments)
      - environment: The current runtime environment (development, production, etc.)

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        A structlog BoundLogger with pre-bound context fields.
    """
    settings = get_settings()
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger.bind(
        service="atlasos",
        environment=settings.ENVIRONMENT,
    )
