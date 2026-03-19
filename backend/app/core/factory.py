from flask import Flask
from app.services.rate_limit.Integration import register_rate_limiting
from app.core.extensions import init_extensions
from app.core.logging import setup_logging, setup_bootstrap_logging
from app.core.config import get_settings, apply_settings_to_flask
from app.api.v1 import register_api_v1


def create_app() -> Flask:
    setup_bootstrap_logging()
    settings = get_settings()  # Load settings early to catch configuration errors before app creation
    app = Flask(__name__)
    setup_logging(app, settings)
    
    apply_settings_to_flask(app, settings)
    init_extensions(app)
    register_api_v1(app)
    register_rate_limiting(app, settings)

    return app