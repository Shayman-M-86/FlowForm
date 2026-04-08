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
    return jsonify(
        data={"timestamp": datetime.now(UTC).isoformat()},
        message="Service is ready",
    ), 200


@health_bp.route("/db", methods=["GET"])
def database_check():
    """Return a database connectivity check response.

    Returns:
        JSON response indicating if the database connection is healthy.
    """
    try:
        db = get_core_db()
        db.execute(text("SELECT 1"))
        core_db = "Core DB connected successfully."
    except Exception as e:
        logger.error(f"Connection to core database failed: {e!s}")
        core_db = "Core DB connection failed."
    try:
        db = get_response_db()
        db.execute(text("SELECT 1"))
        response_db = "Response DB connected successfully."
    except Exception as e:
        logger.error(f"Connection to response database failed: {e!s}")
        response_db = "Response DB connection failed."

    return jsonify(
        data={"timestamp": datetime.now(UTC).isoformat()},
        message=f"Database connectivity check: {core_db} {response_db}",
    ), 200
