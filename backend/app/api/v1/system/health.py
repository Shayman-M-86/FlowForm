from datetime import UTC, datetime
from logging import getLogger
from threading import Lock
from time import monotonic

from flask import current_app, jsonify
from sqlalchemy import text

from app.api.v1.system import system_bp
from app.db.context import get_core_db, get_response_db
from app.openapi import openapi_route

logger = getLogger(__name__)

_READINESS_CACHE_TTL_SECONDS = 10.0
_readiness_cache_lock = Lock()
_readiness_cache: tuple[float, str, int] | None = None


@openapi_route(summary="Health check", tags=["Health"], auth_required=False)
@system_bp.route("/health", methods=["GET"])
def health_check():
    """Return a simple health check response with the current UTC timestamp.

    Returns:
        JSON response indicating the service is healthy.
    """
    return jsonify(
        data={
            "timestamp": datetime.now(UTC).isoformat(),
            "version": current_app.config["APP_VERSION"],
        },
        message="Service is healthy",
    ), 200


@openapi_route(summary="Readiness check", tags=["Health"], auth_required=False)
@system_bp.route("/health/ready", methods=["GET"])
def readiness_check():
    """Return a readiness check response indicating if the service is ready.

    Returns:
        JSON response indicating the service is ready.
    """
    db_status, status_code = db_check()
    return jsonify(
        data={
            "timestamp": datetime.now(UTC).isoformat(),
            "version": current_app.config["APP_VERSION"],
        },
        message=db_status,
    ), status_code


def db_check() -> tuple[str, int]:
    """Return the per-worker cached readiness status for up to ten seconds.

    Holding the lock across a fresh probe prevents concurrent health checks from
    stampeding both databases. A cached failure is deliberately retained for the
    same short window, so a probe storm cannot turn an outage into more load.
    """
    global _readiness_cache

    with _readiness_cache_lock:
        now = monotonic()
        if _readiness_cache is not None:
            checked_at, message, status_code = _readiness_cache
            if now - checked_at < _READINESS_CACHE_TTL_SECONDS:
                return message, status_code

        message, status_code = _perform_db_check()
        _readiness_cache = (monotonic(), message, status_code)
        return message, status_code


def _perform_db_check() -> tuple[str, int]:
    try:
        db = get_core_db()
        db.execute(text("SELECT 1"))
        core_db = None
    except Exception as e:
        logger.error(f"Connection to core database failed: {e!s}")
        core_db = "Core DB connection failed."

    try:
        db = get_response_db()
        db.execute(text("SELECT 1"))
        response_db = None
    except Exception as e:
        logger.error(f"Connection to response database failed: {e!s}")
        response_db = "Response DB connection failed."

    if core_db or response_db:
        return f"Database connectivity Failed: {core_db or ''} {response_db or ''}", 503
    return "Service is ready", 200
