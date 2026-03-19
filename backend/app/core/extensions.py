from pathlib import Path

from flask import Flask
from flask_cors import CORS
# from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from logging import getLogger

logger = getLogger(__name__)


db = SQLAlchemy()
migrate = Migrate()
cors = CORS()


def init_extensions(app: Flask) -> None:
    db.init_app(app)
    logger.debug("Initializing database")
    migration_dir = Path(app.root_path).parent / "migrations"
    migrate.init_app(app, db, directory=str(migration_dir))
    logger.debug("Database initialized with migration directory: %s", migration_dir)
    # jwt_manager.init_app(app)

    origins = app.config.get("CORS_ORIGINS", "*")
    cors.init_app(app, resources={r"/api/*": {"origins": origins}})
    logger.debug("CORS initialized with origins: %s", origins)
