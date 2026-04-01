from logging import getLogger
from pathlib import Path

from flask import Flask
from flask_cors import CORS

# from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

logger = getLogger(__name__)


# Single SQLAlchemy instance for both databases.
# Core models use the default SQLALCHEMY_DATABASE_URI.
# Response models use __bind_key__ = "response" (SQLALCHEMY_BINDS["response"]).
db = SQLAlchemy()
migrate = Migrate()
cors = CORS()


def init_extensions(app: Flask) -> None:
    """Initialize core Flask extensions for the application.

    Args:
        app: Flask application instance.
    """
    db.init_app(app)
    logger.debug("Initializing core database")
    migration_dir = Path(app.root_path).parent / "migrations"
    migrate.init_app(app, db, directory=str(migration_dir))
    logger.debug("Core database initialized with migration directory: %s", migration_dir)

    if app.config.get("SQLALCHEMY_BINDS", {}).get("response"):
        logger.debug("Response database configured via SQLALCHEMY_BINDS")
    else:
        logger.error("Response database not configured via SQLALCHEMY_BINDS")
        raise RuntimeError("Response database configuration is required for the application to function properly")

    # jwt_manager.init_app(app)

    origins = app.config.get("CORS_ORIGINS", "*")
    cors.init_app(app, resources={r"/api/*": {"origins": origins}})
    logger.debug("CORS initialized with origins: %s", origins)
