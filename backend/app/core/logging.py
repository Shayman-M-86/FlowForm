from __future__ import annotations

import json
import logging
import logging.handlers
import time
import re
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, request, g

from app.core.config import Settings
from app.utils.general import get_client_ip, get_log_level


FMT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

HTTP_LOGGER = logging.getLogger("app.http")

RESET = "\x1b[0m"
COLORS = {
    "DEBUG": "\x1b[36m",  # cyan
    "INFO": "\x1b[32m",  # green
    "WARNING": "\x1b[33m",  # yellow
    "ERROR": "\x1b[31m",  # red
    "CRITICAL": "\x1b[41m",  # red background
}


def strip_ansi(value: str) -> str:
    """Strips ANSI escape sequences from a string."""
    return ANSI_RE.sub("", value)


class JsonFormatter(logging.Formatter):
    """Custom logging formatter that outputs logs in JSON format with a consistent structure."""

    def format(self, record: logging.LogRecord) -> str:
        message = strip_ansi(record.getMessage())
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)
        return json.dumps(payload)


class StripAnsiFormatter(logging.Formatter):
    """Custom logging formatter that strips ANSI escape sequences from log messages."""

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        return ANSI_RE.sub("", message)


COLORS = {
    "DEBUG": "\x1b[36m",  # cyan
    "INFO": "\x1b[32m",  # green
    "WARNING": "\x1b[33m",  # yellow
    "ERROR": "\x1b[31m",  # red
    "CRITICAL": "\x1b[41m",  # red background
}

RESET = "\x1b[0m"


class ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        color = COLORS.get(record.levelname, "")
        record.levelname = f"{color}{record.levelname}{RESET}"
        return super().format(record)



def build_stream_handler(
    *,
    json_logs: bool,
    stream: Any = sys.stdout,
) -> logging.Handler:
    """Builds a stream handler for logging."""
    handler = logging.StreamHandler(stream)
    if json_logs:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(ColorFormatter(FMT))
    return handler


def build_file_handler(
    *,
    path: str | Path,
    json_logs: bool,
    maxBytes: int,
    backupCount: int,
    encoding: str = "utf-8",
) -> logging.Handler:
    """Builds a rotating file handler for logging."""
    handler = logging.handlers.RotatingFileHandler(
        path, encoding=encoding, maxBytes=maxBytes, backupCount=backupCount
    )

    if json_logs:
        formatter = JsonFormatter()
    else:
        formatter = StripAnsiFormatter(FMT)
    handler.setFormatter(formatter)
    return handler


def configure_root_logger(
    *,
    level: str = "INFO",
    handlers: list[logging.Handler] | None = None,
    sqlalchemy_level: str = "WARNING",
    werkzeug_level: str = "INFO",
) -> None:
    """Configures the root logger and specific loggers for SQLAlchemy and Werkzeug.
    Args:
        handlers (list[logging.Handler] | None, optional): A list of logging handlers to attach to the root logger.
    """
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    for handler in handlers or []:
        root.addHandler(handler)

    logging.getLogger("sqlalchemy.engine").setLevel(
        getattr(logging, sqlalchemy_level.upper(), logging.WARNING)
    )
    logging.getLogger("werkzeug").setLevel(
        getattr(logging, werkzeug_level.upper(), logging.INFO)
    )


def log_request(response, duration: float | None = None) -> None:
    """Logs an HTTP request with relevant information such as client IP, method, path, status code, and optionally duration."""
    ip = get_client_ip()
    log_level = get_log_level(response.status_code)

    message = "%s | %s %s -> %s"
    args = [ip, request.method, request.path, response.status_code]

    if duration is not None:
        message += " | (%.2f ms)"
        args.append(duration * 1000)

    HTTP_LOGGER.log(log_level, message, *args)


def register_request_logging(app: Flask, include_duration: bool) -> None:
    """Registers before_request and after_request handlers to log HTTP requests. Optionally includes request duration in the logs."""
    if app.extensions.get("request_logging_registered"):
        return

    if include_duration:

        @app.before_request
        def start_timer():
            g._start_time = time.perf_counter()

    @app.after_request
    def log_response(response):
        duration: float | None = None

        if include_duration:
            start_time = getattr(g, "_start_time", None)
            if start_time is not None:
                duration = time.perf_counter() - start_time

        log_request(response, duration)
        return response

    app.extensions["request_logging_registered"] = True


def setup_logging(app: Flask, settings: Settings) -> None:
    """
    Sets up logging based on the provided settings. This includes configuring the root logger and specific loggers for SQLAlchemy and Werkzeug.
    Expects settings
    """
    log_config = settings.logging
    json_logs = log_config.log_json
    handlers: list[logging.Handler] = [
        build_stream_handler(json_logs=json_logs, stream=sys.stdout),
    ]

    log_file: str | None = log_config.log_file

    if log_file:
        handlers.append(
            build_file_handler(
                path=log_file,
                json_logs=json_logs,
                maxBytes=log_config.log_file_max_bytes,
                backupCount=log_config.log_file_backup_count,
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
    """Sets up basic logging configuration for the bootstrap phase of the application."""
    configure_root_logger(
        level="INFO",
        handlers=[
            build_stream_handler(json_logs=False, stream=sys.stderr),
            build_file_handler(json_logs=False, path="logs/bootstrap.log", maxBytes=5 * 1024 * 1024, backupCount=5),
        ],
        
    )



def log_startup(app: Flask, settings: Settings) -> None:
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return
    logger = logging.getLogger("app.startup")
    if settings.env == "prod":
        log = logging.INFO
    else:
        log = logging.DEBUG
        
    logger.log(
        log,
        "Running on http://%s:%s | Environment: %s",
        settings.server.host,
        settings.server.port,
        settings.env
    )
