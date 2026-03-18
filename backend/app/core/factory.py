from flask import Flask
from app.core.extensions import init_extensions
from app.core.logging import setup_logging, setup_bootstrap_logging
from app.core.config import get_settings
from app.api.v1 import register_api_v1


def create_app(config_object: str) -> Flask:
    setup_bootstrap_logging()
    settings = get_settings()  # Load settings early to catch configuration errors before app creation
    setup_logging(settings)
    
    app = Flask(__name__)
    app.config.from_object(config_object)
    init_extensions(app, jwt_manager)
    register_api_v1(app)

    return app