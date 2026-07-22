from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from flask import Flask, g, request

from app.utils.general import get_client_ip, get_log_level

HTTP_LOGGER = logging.getLogger("app.http")
logger = logging.getLogger(__name__)

_UNMATCHED_REQUEST_PATH = "<unmatched>"


def get_request_log_path() -> str:
    """Return a stable route template without caller-provided path values."""
    if request.url_rule is None:
        return _UNMATCHED_REQUEST_PATH
    return request.url_rule.rule


def log_request(response, duration_seconds: float | None = None) -> None:
    """Log a completed HTTP request with structured metadata."""
    ip = get_client_ip()
    log_level = get_log_level(response.status_code)
    path = get_request_log_path()

    extra: dict[str, Any] = {
        "request_id": getattr(g, "request_id", None),
        "method": request.method,
        "path": path,
        "status_code": response.status_code,
        "remote_addr": ip,
    }

    duration_ms = round(duration_seconds * 1000, 2) if duration_seconds is not None else None
    if duration_ms is not None:
        extra["duration_ms"] = duration_ms

    message = "%s | %s %s -> %s"
    args: tuple[Any, ...] = (ip, request.method, path, response.status_code)
    if duration_ms is not None:
        message = f"{message} duration_ms=%s"
        args = (*args, duration_ms)

    HTTP_LOGGER.log(
        log_level,
        message,
        *args,
        extra=extra,
    )


def register_request_logging(app: Flask, *, include_duration: bool) -> None:
    """Register request logging hooks once per app instance.

    Args:
        app: Flask application instance.
        include_duration: Whether to record request duration in logs.
    """
    if app.extensions.get("request_logging_registered"):
        return

    logger.debug("Registering before_request logging (include_duration=%s)", include_duration)

    @app.before_request
    def before_request_logging() -> None:
        g.request_id = str(uuid.uuid4())
        g.request_started_at = time.perf_counter()
        g.request_last_timing_at = g.request_started_at

    logger.debug("Registering after request hook for request logging")
    @app.after_request
    def after_request_logging(response):
        duration_seconds: float | None = None

        if include_duration:
            started_at = getattr(g, "request_started_at", None)
            if started_at is not None:
                duration_seconds = time.perf_counter() - started_at

        log_request(response, duration_seconds)
        response.headers["X-Request-ID"] = g.request_id
        return response

    app.extensions["request_logging_registered"] = True
