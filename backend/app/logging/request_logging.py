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

# Caddy stamps X-Request-ID = {http.request.uuid} and logs it, so adopting it
# gives one request_id shared across the Caddy and backend lines for joining in
# Loki. The header is client-influenced, so we accept ONLY a well-formed UUID —
# echoing arbitrary text into structured logs (and the response header) would let
# a caller inject log fields or response-splitting payloads. Else → mint our own.
_REQUEST_ID_HEADER = "X-Request-ID"

# The longest form uuid.UUID accepts is the 45-char "urn:uuid:" prefix; anything
# longer can't be a UUID, so we reject it before the parser — capping the work
# done on a hostile oversized header.
_MAX_REQUEST_ID_LEN = 45


def _resolve_request_id() -> str:
    """Adopt a valid inbound X-Request-ID (from Caddy), else mint a fresh one.

    Accepted values are normalised to canonical UUID string form, so what we log
    and echo is always our own rendering, never the caller's raw bytes. Malformed
    headers are rejected and logged (to surface a misbehaving upstream) but never
    raise — request logging must not be able to fail a request.
    """
    inbound = request.headers.get(_REQUEST_ID_HEADER)
    if not inbound:
        return str(uuid.uuid4())

    if len(inbound) <= _MAX_REQUEST_ID_LEN:
        try:
            return str(uuid.UUID(inbound))
        except (ValueError, TypeError):
            pass

    # Never log the raw value (the injection vector); %.60r escapes control chars
    # and caps length so an oversized header can't bloat the log line.
    logger.warning(
        "Ignoring malformed inbound %s header (len=%d); minting a fresh request_id. value=%.60r",
        _REQUEST_ID_HEADER,
        len(inbound),
        inbound,
    )
    return str(uuid.uuid4())


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
        g.request_id = _resolve_request_id()
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
