from __future__ import annotations

import json
import logging
import logging.handlers
import os
import re
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from flask import Flask

from app.core.config import Settings
from app.logging.request_logging import register_request_logging
from app.logging.sensitive_data import install_sensitive_data_filter, protect_root_handlers

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

THIRD_PARTY_LOG_LEVELS: dict[str, int] = {
    "auth0_api_python": logging.WARNING,
    "authlib": logging.WARNING,
    "boto3": logging.WARNING,
    "botocore": logging.WARNING,
    "hpack": logging.WARNING,
    "httpcore": logging.WARNING,
    "httpx": logging.WARNING,
    "sqlalchemy.engine": logging.WARNING,
    "urllib3": logging.WARNING,
    "werkzeug": logging.INFO,
}


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
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": strip_ansi(record.getMessage()),
        }

        # Canonical field names shared across the whole log suite (backend,
        # caddy, squid): the LogRecord attribute on the left maps to the JSON
        # key on the right. Renames (status_code -> status, remote_addr ->
        # client_ip) unify field names across services so a single Loki query
        # works fleet-wide. Alloy stages key off these JSON names.
        record_attr_to_json_key = {
            "request_id": "request_id",
            "method": "method",
            "path": "path",
            "status_code": "status",
            "remote_addr": "client_ip",
            "user_id": "user_id",
            "event_type": "event_type",
            "environment": "environment",
            "resource_type": "resource_type",
            "resource_id": "resource_id",
            "duration_ms": "duration_ms",
            "step_delta_ms": "step_delta_ms",
            "timing_label": "timing_label",
            "metadata": "metadata",
        }
        for attr, json_key in record_attr_to_json_key.items():
            value = getattr(record, attr, None)
            if value is not None:
                payload[json_key] = value

        trace_id = getattr(record, "otelTraceID", None)
        span_id = getattr(record, "otelSpanID", None)
        if trace_id not in (None, 0, "0"):
            payload["trace_id"] = trace_id
        if span_id not in (None, 0, "0"):
            payload["span_id"] = span_id

        if record.exc_info:
            payload["exception"] = record.exc_text or self.formatException(record.exc_info)

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


class PrivateRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """Keep the active and newly rotated application log files owner-only."""

    def _open(self):
        stream = super()._open()
        os.chmod(self.baseFilename, 0o600)
        return stream


def build_stream_handler(
    *,
    json_logs: bool,
    stream: Any = sys.stdout,
) -> logging.Handler:
    """Build a stream handler."""
    handler = logging.StreamHandler(stream)
    install_sensitive_data_filter(handler)
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

    handler = PrivateRotatingFileHandler(
        filename=path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding=encoding,
    )
    install_sensitive_data_filter(handler)
    formatter: logging.Formatter = (
        JsonFormatter() if json_logs else StripAnsiFormatter(LOG_FORMAT)
    )
    handler.setFormatter(formatter)
    return handler


# =============================================================================
# Root logger configuration
# =============================================================================


def configure_third_party_loggers(
    overrides: Mapping[str, int] | None = None,
) -> None:
    """Keep dependency diagnostics below levels that expose wire data."""
    levels = {**THIRD_PARTY_LOG_LEVELS, **(overrides or {})}
    for logger_name, logger_level in levels.items():
        logging.getLogger(logger_name).setLevel(logger_level)


def configure_root_logger(
    *,
    level: str = "INFO",
    handlers: list[logging.Handler] | None = None,
    sqlalchemy_level: str = "WARNING",
    werkzeug_level: str = "INFO",
    botocore_level: str = "WARNING",
    authlib_level: str = "WARNING",
    auth0_level: str = "WARNING",
    urllib3_level: str = "WARNING",
) -> None:
    """Configure the root logger and selected third-party loggers."""
    root = logging.getLogger()
    protect_root_handlers()

    for handler in root.handlers[:]:
        if not getattr(handler, "_app_owned_handler", False):
            continue

        root.removeHandler(handler)
        try:
            handler.flush()
        finally:
            handler.close()

    root.setLevel(resolve_log_level(level))

    for handler in handlers or []:
        install_sensitive_data_filter(handler)
        setattr(handler, "_app_owned_handler", True)  # noqa: B010
        root.addHandler(handler)

    configure_third_party_loggers(
        {
            "auth0_api_python": resolve_log_level(auth0_level, logging.WARNING),
            "authlib": resolve_log_level(authlib_level, logging.WARNING),
            "botocore": resolve_log_level(botocore_level, logging.WARNING),
            "sqlalchemy.engine": resolve_log_level(sqlalchemy_level, logging.WARNING),
            "urllib3": resolve_log_level(urllib3_level, logging.WARNING),
            "werkzeug": resolve_log_level(werkzeug_level, logging.INFO),
        }
    )


# =============================================================================
# Startup logging
# =============================================================================


def log_startup(app: Flask, settings: Settings) -> None:
    """Log application startup details once per server process.

    Emits two INFO lines: a boot-success confirmation and an explicit
    environment banner. Runs under both the Flask dev server and gunicorn.

    Under the Flask dev reloader the parent process spawns a child that does the
    real serving (WERKZEUG_RUN_MAIN=true); logging in both would double the
    banner, so skip the parent. Gunicorn sets no such marker, so the check only
    suppresses the reloader's parent, never the real prod/rehearsal boot.
    """
    if "WERKZEUG_RUN_MAIN" in os.environ and os.environ["WERKZEUG_RUN_MAIN"] != "true":
        return

    STARTUP_LOGGER.info(
        "FlowForm backend started successfully | version=%s | listening on http://%s:%s | debug=%s",
        settings.flowform.app.version,
        settings.flowform.server.host,
        settings.flowform.server.port,
        app.debug,
        extra={"event_type": "app_startup"},
    )
    STARTUP_LOGGER.info(
        "Running in %s environment",
        settings.flowform.env,
        extra={"event_type": "app_startup", "environment": settings.flowform.env},
    )


# =============================================================================
# Public setup functions
# =============================================================================


def setup_logging(app: Flask, settings: Settings) -> None:
    """Configure root logging from application settings."""
    log_config = settings.flowform.logging
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
