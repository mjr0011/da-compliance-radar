"""
Structured logging configuration.

Production logs are JSON for ingestion by Loki/Datadog/etc. Development
logs are pretty-printed for readability.

Call `setup_logging()` once at app start (main.py + celery_app.py).
"""
from __future__ import annotations

import logging
import sys

import structlog

from app.config import settings


def setup_logging() -> None:
    is_prod = settings.environment == "production"

    timestamper = structlog.processors.TimeStamper(fmt="iso")

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.JSONRenderer()
            if is_prod
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.INFO if is_prod else logging.DEBUG
        ),
        cache_logger_on_first_use=True,
    )

    # Route standard library logging through the same processors so
    # 3rd-party libs (uvicorn, sqlalchemy, celery) emit consistent
    # output.
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processor=(
            structlog.processors.JSONRenderer()
            if is_prod
            else structlog.dev.ConsoleRenderer()
        ),
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO if is_prod else logging.DEBUG)

    # Quiet some noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str | None = None):
    return structlog.get_logger(name)
