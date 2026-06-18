from datetime import UTC, datetime
from logging import getLogger

from flask import jsonify
from sqlalchemy import text

from app.api.v1.system import system_bp
from app.db.context import get_core_db, get_response_db
from app.openapi import openapi_route

logger = getLogger(__name__)


@openapi_route(summary="Health check", tags=["Health"], auth_required=False)
@system_bp.route("/health", methods=["GET"])
def health_check():
    """Return a simple health check response with the current UTC timestamp.

    Returns:
        JSON response indicating the service is healthy.
    """
    return jsonify(
        data={"timestamp": datetime.now(UTC).isoformat()},
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
        data={"timestamp": datetime.now(UTC).isoformat()},
        message=db_status,
    ), status_code


def db_check():
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
