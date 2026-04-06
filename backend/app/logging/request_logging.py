from __future__ import annotations

import logging
import time
import uuid
from typing import Any
from venv import logger

from flask import Flask, g, request

from app.utils.general import get_client_ip, get_log_level

HTTP_LOGGER = logging.getLogger("app.http")


def log_request(response, duration_seconds: float | None = None) -> None:
    """Log a completed HTTP request with structured metadata."""
    ip = get_client_ip()
    log_level = get_log_level(response.status_code)

    extra: dict[str, Any] = {
        "request_id": getattr(g, "request_id", None),
        "method": request.method,
        "path": request.path,
        "status_code": response.status_code,
        "remote_addr": ip,
    }

    if duration_seconds is not None:
        extra["duration_ms"] = round(duration_seconds * 1000, 2)

    HTTP_LOGGER.log(
        log_level,
        "%s | %s %s -> %s",
        ip,
        request.method,
        request.path,
        response.status_code,
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
    
    logger.debug(f"Registering before_request logging (include_duration={include_duration})")
    @app.before_request
    def before_request_logging() -> None:
        g.request_id = str(uuid.uuid4())
        if include_duration:
            g.request_started_at = time.perf_counter()
    
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
