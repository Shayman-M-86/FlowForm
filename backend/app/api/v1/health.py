from datetime import UTC, datetime

from flask import Blueprint

from app.core.responses import SuccessResponse, success_response

health_bp = Blueprint("health_v1", __name__, url_prefix="/health")


@health_bp.route("/", methods=["GET"])
def health_check():
    """Return a simple health check response with the current UTC timestamp.

    Returns:
        JSON response indicating the service is healthy.
    """
    return SuccessResponse.return_it(
        data={"timestamp": datetime.now(UTC).isoformat()},
        message="Service is healthy",
    )


@health_bp.route("/ready", methods=["GET"])
def readiness_check():
    """Return a readiness check response indicating if the service is ready.

    Returns:
        JSON response indicating the service is ready.
    """
    return success_response(
        data={"timestamp": datetime.now(UTC).isoformat()},
        message="Service is ready",
    )
