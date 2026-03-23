from __future__ import annotations

import json
import logging
import logging.handlers
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from flask import Flask

from app.core.config import Settings
from app.logging.request_logging import register_request_logging

# =============================================================================
# Constants
# =============================================================================

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

RESET = "\x1b[0m"
LEVEL_COLORS = {
    "DEBUG": "\x1b[36m",
    "INFO": "\x1b[32m",
    "WARNING": "\x1b[33m",
    "ERROR": "\x1b[31m",
    "CRITICAL": "\x1b[41m",
}

STARTUP_LOGGER = logging.getLogger("app.startup")


# =============================================================================
# Helpers
# =============================================================================


def strip_ansi(value: str) -> str:
    """Remove ANSI escape sequences from a string."""
    return ANSI_RE.sub("", value)


def resolve_log_level(level: str, default: int = logging.INFO) -> int:
    """Convert a log level string to a logging module integer level."""
    return getattr(logging, level.upper(), default)


def ensure_parent_dir(path: str | Path) -> None:
    """Ensure the parent directory for a log file exists."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Formatters
# =============================================================================


class JsonFormatter(logging.Formatter):
    """Format log records as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Convert a LogRecord to a JSON string, including extra fields and exception info."""
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": strip_ansi(record.getMessage()),
        }

        for attr in (
            "request_id",
            "method",
            "path",
            "status_code",
            "remote_addr",
            "user_id",
            "event_type",
            "resource_type",
            "resource_id",
            "duration_ms",
            "metadata"
        ):
            value = getattr(record, attr, None)
            if value is not None:
                payload[attr] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)

        return json.dumps(payload, default=str)


class StripAnsiFormatter(logging.Formatter):
    """Format logs as plain text with ANSI sequences removed."""

    def format(self, record: logging.LogRecord) -> str:
        """Remove ANSI escape sequences from the formatted log message."""
        return strip_ansi(super().format(record))


class ColorFormatter(logging.Formatter):
    """Format logs as colored terminal text."""

    def format(self, record: logging.LogRecord) -> str:
        original_levelname = record.levelname
        color = LEVEL_COLORS.get(original_levelname, "")

        try:
            record.levelname = f"{color}{original_levelname}{RESET}"
            return super().format(record)
        finally:
            record.levelname = original_levelname


# =============================================================================
# Handler builders
# =============================================================================


def build_stream_handler(
    *,
    json_logs: bool,
    stream: Any = sys.stdout,
) -> logging.Handler:
    """Build a stream handler."""
    handler = logging.StreamHandler(stream)
    formatter: logging.Formatter = (
        JsonFormatter() if json_logs else ColorFormatter(LOG_FORMAT)
    )
    handler.setFormatter(formatter)
    return handler


def build_file_handler(
    *,
    path: str | Path,
    json_logs: bool,
    max_bytes: int,
    backup_count: int,
    encoding: str = "utf-8",
) -> logging.Handler:
    """Build a rotating file handler."""
    ensure_parent_dir(path)

    handler = logging.handlers.RotatingFileHandler(
        filename=path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding=encoding,
    )
    formatter: logging.Formatter = (
        JsonFormatter() if json_logs else StripAnsiFormatter(LOG_FORMAT)
    )
    handler.setFormatter(formatter)
    return handler


# =============================================================================
# Root logger configuration
# =============================================================================


def configure_root_logger(
    *,
    level: str = "INFO",
    handlers: list[logging.Handler] | None = None,
    sqlalchemy_level: str = "WARNING",
    werkzeug_level: str = "INFO",
) -> None:
    """Configure the root logger and selected third-party loggers."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(resolve_log_level(level))

    for handler in handlers or []:
        root.addHandler(handler)

    logging.getLogger("sqlalchemy.engine").setLevel(
        resolve_log_level(sqlalchemy_level, logging.WARNING)
    )
    logging.getLogger("werkzeug").setLevel(
        resolve_log_level(werkzeug_level, logging.INFO)
    )


# =============================================================================
# Startup logging
# =============================================================================


def log_startup(app: Flask, settings: Settings) -> None:
    """Log application startup details once in the active Werkzeug process."""
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    level = logging.INFO if settings.env == "prod" else logging.DEBUG

    STARTUP_LOGGER.log(
        level,
        "Running on http://%s:%s | Environment: %s | Debug: %s",
        settings.server.host,
        settings.server.port,
        settings.env,
        app.debug,
    )


# =============================================================================
# Public setup functions
# =============================================================================


def setup_logging(app: Flask, settings: Settings) -> None:
    """Configure root logging from application settings."""
    log_config = settings.logging
    json_logs = log_config.log_json

    handlers: list[logging.Handler] = [
        build_stream_handler(json_logs=json_logs, stream=sys.stdout),
    ]

    if log_config.log_file:
        handlers.append(
            build_file_handler(
                path=log_config.log_file,
                json_logs=json_logs,
                max_bytes=log_config.log_file_max_bytes,
                backup_count=log_config.log_file_backup_count,
            )
        )

    configure_root_logger(
        level=log_config.level,
        handlers=handlers,
        sqlalchemy_level=log_config.sqlalchemy_level,
        werkzeug_level=log_config.werkzeug_level,
    )

    if log_config.requests:
        register_request_logging(app, include_duration=log_config.duration)

    log_startup(app, settings)


def setup_bootstrap_logging() -> None:
    """Configure minimal logging for early bootstrap/app startup."""
    configure_root_logger(
        level="INFO",
        handlers=[
            build_stream_handler(json_logs=False, stream=sys.stderr),
            build_file_handler(
                path="logs/bootstrap.log",
                json_logs=False,
                max_bytes=5 * 1024 * 1024,
                backup_count=5,
            ),
        ],
    )
