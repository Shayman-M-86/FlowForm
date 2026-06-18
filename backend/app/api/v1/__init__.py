import logging

from flask import Blueprint, Flask

from app.api.v1.account import account_bp
from app.api.v1.respondent import respondent_bp
from app.api.v1.studio import studio_projects_bp
from app.api.v1.system import system_bp

__all__ = ["register_api_v1"]

LOGGER = logging.getLogger(__name__)

ROUTES: list[tuple[Blueprint, str]] = [
    (account_bp, "/api/v1/account"),
    (studio_projects_bp, "/api/v1/studio/projects"),
    (respondent_bp, "/api/v1/respondent"),
    (system_bp, "/api/v1/system"),
]


def register_api_v1(app: Flask) -> None:
    """Register all version 1 API blueprints on the Flask app.

    Args:
        app: Flask application instance.
    """
    for bp, prefix in ROUTES:
        if not bp.name.endswith("_v1"):
            raise ValueError(f"Blueprint {bp.name} does not end with '_v1'")

        LOGGER.debug(f"Registering blueprint {bp.name} at {prefix}")
        app.register_blueprint(bp, url_prefix=prefix)
