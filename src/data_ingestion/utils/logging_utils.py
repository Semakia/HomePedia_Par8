"""Structured logging for the ingestion layer.

Console renderer in dev, JSON in any other environment so logs are
machine-parseable in prod. Call `configure_logging()` once at process start
(connectors do this in their __main__), then `get_logger(__name__)` everywhere.
"""

from __future__ import annotations

import logging
import os

import structlog


def configure_logging(level: str | None = None) -> None:
    """Configure structlog + stdlib logging. Idempotent."""
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    is_dev = os.getenv("ENVIRONMENT", "development") == "development"

    logging.basicConfig(format="%(message)s", level=log_level)

    renderer = (
        structlog.dev.ConsoleRenderer()
        if is_dev
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    return structlog.get_logger(name)
