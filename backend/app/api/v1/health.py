from datetime import UTC, datetime
from logging import getLogger

from flask import Blueprint, jsonify
from sqlalchemy import text

from app.db.context import get_core_db, get_response_db

health_bp = Blueprint("health_v1", __name__, url_prefix="/health")

logger = getLogger(__name__)


@health_bp.route("/", methods=["GET"])
def health_check():
    """Return a simple health check response with the current UTC timestamp.

    Returns:
        JSON response indicating the service is healthy.
    """
    return jsonify(
        data={"timestamp": datetime.now(UTC).isoformat()},
        message="Service is healthy",
    ), 200


@health_bp.route("/ready", methods=["GET"])
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
