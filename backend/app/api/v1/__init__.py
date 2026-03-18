import logging

from flask import Flask, Blueprint

from app.api.v1.auth import auth_bp
from app.api.v1.health import health_bp
from app.api.v1.questionnaires import questionnaires_bp

__all__ = ["register_api_v1"]

LOGGER = logging.getLogger(__name__)

ROUTES: list[Blueprint] = [
    health_bp, 
    auth_bp, 
    questionnaires_bp
]

def register_api_v1(app: Flask) -> None:
    for bp in ROUTES:
        if not bp.name.endswith("v1"):
            raise ValueError(f"Blueprint {bp.name} does not end with 'v1'")
    for bp in ROUTES:
        app.register_blueprint(bp)
