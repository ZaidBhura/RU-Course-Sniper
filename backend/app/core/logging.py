"""Structured logging configuration via structlog.

Call configure_logging() once at process startup (FastAPI lifespan or Celery
worker_process_init signal). All subsequent calls to structlog.get_logger()
will use the configured renderer and processors.

Processor chain (in order):
  1. merge_contextvars   — injects request_id / tenant_id bound via contextvars
  2. add_log_level       — adds "level" field
  3. add_logger_name     — adds "logger" field
  4. TimeStamper         — adds "timestamp" in ISO 8601
  5. StackInfoRenderer   — renders stack_info if present
  6. SecretScrubber      — replaces sensitive field values with [REDACTED]
  7. format_exc_info     — formats exc_info into "exception" string
  8. renderer            — JSONRenderer (prod) or ConsoleRenderer (dev)

Stdlib bridge: uvicorn / SQLAlchemy / Celery still emit stdlib logging.Logger
records. ProcessorFormatter routes those through the same pipeline so all logs
share a consistent format.
"""

import logging
import logging.config
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "secret_key",
        "fernet_key",
        "webhook_url",
        "discord_url",
        "pushover_key",
        "authorization",
        "credential",
        "credential_blob",
        "api_key",
    }
)


def _add_logger_name(logger: Any, _method: str, event_dict: EventDict) -> EventDict:
    """Add logger name to the event dict.

    structlog.stdlib.add_logger_name requires a stdlib Logger with .name, which
    PrintLogger doesn't have. This version gracefully handles both.
    """
    record = event_dict.get("_record")
    if record is not None:
        event_dict["logger"] = record.name
    else:
        name = getattr(logger, "name", None) or getattr(logger, "_name", None)
        if name is not None:
            event_dict["logger"] = name
    return event_dict


def _scrub_secrets(_logger: Any, _method: str, event_dict: EventDict) -> EventDict:
    """Redact values whose key matches a sensitive field name."""
    for key in list(event_dict.keys()):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = "[REDACTED]"
    return event_dict


def _build_processors(dev: bool) -> list[Processor]:
    shared: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        _add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        _scrub_secrets,
    ]
    if dev:
        shared.append(structlog.dev.ConsoleRenderer())
    else:
        # format_exc_info must run before JSONRenderer (converts tuple → string).
        shared.append(structlog.processors.format_exc_info)
        shared.append(structlog.processors.JSONRenderer())
    return shared


def configure_logging(dev: bool | None = None) -> None:
    """Configure structlog and the stdlib root logger.

    If *dev* is not passed, it is inferred from the ENVIRONMENT setting:
    any value other than "production" or "staging" is treated as dev mode.
    """
    if dev is None:
        try:
            from app.core.config import settings

            dev = settings.ENVIRONMENT not in ("production", "staging")
            level_name = settings.LOG_LEVEL.upper()
        except Exception:
            dev = True
            level_name = "INFO"
    else:
        level_name = "INFO"

    level = getattr(logging, level_name, logging.INFO)

    processors = _build_processors(dev)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Route stdlib logging through structlog's ProcessorFormatter so that
    # uvicorn, SQLAlchemy, and Celery log records are formatted identically.
    stdlib_processors: list[Processor] = [
        structlog.stdlib.add_log_level,
        _add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        _scrub_secrets,
        structlog.processors.format_exc_info,
    ]
    if dev:
        stdlib_processors.append(structlog.dev.ConsoleRenderer())
    else:
        stdlib_processors.append(structlog.processors.JSONRenderer())

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=stdlib_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Quiet noisy third-party loggers.
    for noisy in ("httpx", "httpcore", "asyncio", "hpack"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
