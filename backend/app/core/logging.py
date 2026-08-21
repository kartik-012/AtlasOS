"""
AtlasOS Structured Logging Configuration.

Configures structlog (with fallback to stdlib logging) for consistent,
machine-parseable log output across the entire backend application and Celery workers.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

try:
    import structlog
    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False

from app.core.config import get_settings


class StdlibLoggerWrapper:
    """Fallback wrapper matching structlog interface when structlog is not present."""

    def __init__(self, logger: logging.Logger, context: dict[str, Any] | None = None) -> None:
        self._logger = logger
        self._context = context or {}

    def bind(self, **kwargs: Any) -> StdlibLoggerWrapper:
        new_ctx = {**self._context, **kwargs}
        return StdlibLoggerWrapper(self._logger, new_ctx)

    def info(self, event: str, **kwargs: Any) -> None:
        merged = {**self._context, **kwargs}
        self._logger.info(f"{event} {merged if merged else ''}")

    def warning(self, event: str, **kwargs: Any) -> None:
        merged = {**self._context, **kwargs}
        self._logger.warning(f"{event} {merged if merged else ''}")

    def error(self, event: str, **kwargs: Any) -> None:
        merged = {**self._context, **kwargs}
        self._logger.error(f"{event} {merged if merged else ''}")

    def exception(self, event: str, **kwargs: Any) -> None:
        merged = {**self._context, **kwargs}
        self._logger.exception(f"{event} {merged if merged else ''}")

    def critical(self, event: str, **kwargs: Any) -> None:
        merged = {**self._context, **kwargs}
        self._logger.critical(f"{event} {merged if merged else ''}")


def setup_logging() -> None:
    """Configure structlog and stdlib logging for the application."""
    settings = get_settings()
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    if not HAS_STRUCTLOG:
        logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        return

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.is_production:
        renderer = structlog.processors.JSONRenderer()
    else:
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


def get_logger(name: str) -> Any:
    """Create a logger with service context."""
    settings = get_settings()
    if HAS_STRUCTLOG:
        logger = structlog.get_logger(name)
        return logger.bind(
            service="atlasos",
            environment=settings.ENVIRONMENT,
        )
    return StdlibLoggerWrapper(logging.getLogger(name), {"service": "atlasos", "environment": settings.ENVIRONMENT})
