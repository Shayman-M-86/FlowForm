from logging import getLogger

from flask import Flask
from flask_cors import CORS

# from flask_jwt_extended import JWTManager
from app.db.manager import DatabaseManager

logger = getLogger(__name__)


db_manager = DatabaseManager()
cors = CORS()


def init_extensions(app: Flask) -> None:
    """Initialize core Flask extensions for the application.

    Args:
        app: Flask application instance.
    """
    logger.debug("Initializing core database")
    db_manager.init_app(app)


    # jwt_manager.init_app(app)

    origins = app.config.get("CORS_ORIGINS", "*")
    cors.init_app(app, resources={r"/api/*": {"origins": origins}})
    logger.debug("CORS initialized with origins: %s", origins)
