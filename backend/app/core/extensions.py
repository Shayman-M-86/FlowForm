from logging import getLogger

from flask import Flask
from flask_cors import CORS

from app.aws import AwsClientManager
from app.cache import create_app_cache
from app.core.config import CorsSettings, Settings
from app.db.manager import DatabaseManager
from app.email_service import EmailServiceManager
from app.middleware.auth import AuthExtension
from app.middleware.url_converters import register_url_converters

logger = getLogger(__name__)

aws_client_manager = AwsClientManager()
app_cache = create_app_cache()

email_service_manager = EmailServiceManager()
db_manager = DatabaseManager()
auth = AuthExtension()
cors = CORS()


def init_extensions(app: Flask, settings: Settings) -> None:
    """Initialize core Flask extensions for the application."""
    app_cache.init_app(app)

    aws_client_manager.init_app(app)
    email_service_manager.init_app(app)
    logger.debug("Initializing core database")
    db_manager.init_app(app)
    auth.init_app(app)
    register_url_converters(app)

    init_cors(app, settings.flowform.cors)


def init_cors(app: Flask, settings: CorsSettings) -> None:
    """Configure CORS from the validated application settings."""
    cors.init_app(
        app,
        resources={
            r"/api/*": {
                "origins": settings.origins,
                "allow_headers": ["Content-Type", "Authorization"],
                "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                "supports_credentials": settings.supports_credentials,
            }
        },
    )
    logger.debug("CORS initialized with origins: %s", settings.origins)
