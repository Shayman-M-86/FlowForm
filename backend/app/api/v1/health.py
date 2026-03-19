from datetime import datetime, timezone

from flask import Blueprint

from app.core.responses import success_response

health_bp = Blueprint("health_v1", __name__, url_prefix="/health")

@health_bp.route("/", methods=["GET"])
def health_check():
    return success_response(data={"timestamp": datetime.now(timezone.utc).isoformat()}, message="Service is healthy")
