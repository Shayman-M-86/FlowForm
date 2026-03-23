from flask import Flask

from app.api.v1 import register_api_v1
from app.core.config import apply_settings_to_flask, get_settings
from app.core.extensions import init_extensions
from app.logging.logging_config import setup_bootstrap_logging, setup_logging
from app.middleware.rate_limit import register_rate_limiting


def create_app() -> Flask:
    """Application factory function."""
    setup_bootstrap_logging()
    settings = get_settings()
    app = Flask(__name__)
    setup_logging(app, settings)

    apply_settings_to_flask(app, settings)
    init_extensions(app)
    register_api_v1(app)
    register_rate_limiting(app, settings)

    return app
