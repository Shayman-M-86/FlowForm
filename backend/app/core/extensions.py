from logging import getLogger

from flask import Flask
from flask_cors import CORS

# from flask_jwt_extended import JWTManager
from app.crypto.cache import CryptoKeyCache
from app.crypto.services.provider import init_crypto_services
from app.db.manager import DatabaseManager
from app.middleware.auth import AuthExtension
from app.middleware.url_converters import register_url_converters

logger = getLogger(__name__)


crypto_key_cache = CryptoKeyCache()
db_manager = DatabaseManager()
auth = AuthExtension()
cors = CORS()


def init_extensions(app: Flask) -> None:
    """Initialize core Flask extensions for the application.

    Args:
        app: Flask application instance.
    """
    settings = app.extensions["settings"]
    enc = settings.flowform.encryption
    key_cache_enabled = enc.key_cache_enabled if enc is not None else True
    crypto_key_cache.init_app(app, enabled=key_cache_enabled)
    init_crypto_services(app, cache=crypto_key_cache)
    logger.debug("Initializing core database")
    db_manager.init_app(app)
    auth.init_app(app)
    register_url_converters(app)


    # jwt_manager.init_app(app)

    origins = app.config.get("CORS_ORIGINS", "*")
    cors.init_app(app, resources={r"/api/*": {
        "origins": origins,
        "allow_headers": ["Content-Type", "Authorization"],
        "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "supports_credentials": True,
    }})
    logger.debug("CORS initialized with origins: %s", origins)
