import logging

from flask import Blueprint, Flask

from app.api.v1.auth import auth_bp
from app.api.v1.health import health_bp
from app.api.v1.projects import projects_bp
from app.api.v1.public import public_bp

__all__ = ["register_api_v1"]

LOGGER = logging.getLogger(__name__)

ROUTES: list[Blueprint] = [
    auth_bp,
    health_bp,
    projects_bp,
    public_bp,
]


def register_api_v1(app: Flask) -> None:
    """Register all version 1 API blueprints on the Flask app.

    Args:
        app: Flask application instance.
    """
    for bp in ROUTES:
        if not bp.name.endswith("_v1"):
            raise ValueError(f"Blueprint {bp.name} does not end with '_v1'")

        resource = bp.name.removesuffix("_v1")
        prefix = f"/api/v1/{resource}"

        LOGGER.debug(f"Registering blueprint {bp.name} at {prefix}")
        app.register_blueprint(bp, url_prefix=prefix)
