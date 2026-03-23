import logging

from flask import g, request


def to_bool(value: str) -> bool:
    """Return True if a string represents a truthy value."""
    return value.lower() in {"true", "1", "yes", "on"}


def get_client_ip() -> str:
    """Return the client IP address, preferring ``X-Forwarded-For`` when present."""
    if hasattr(g, "client_ip"):
        return g.client_ip

    xff = request.headers.get("X-Forwarded-For")
    ip = xff.partition(",")[0].strip() if xff else request.remote_addr or "unknown"

    g.client_ip = ip
    return ip


def get_log_level(status_code: int) -> int:
    """Map an HTTP status code to an appropriate logging level."""
    if status_code >= 500:
        return logging.ERROR
    if status_code >= 400:
        return logging.WARNING
    if status_code >= 300:
        return logging.INFO
    return logging.DEBUG
