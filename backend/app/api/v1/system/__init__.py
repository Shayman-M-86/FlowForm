from flask import Blueprint

system_bp = Blueprint("system_v1", __name__)

from app.api.v1.system import health  # noqa: E402
