from collections.abc import Mapping
from typing import Any

from flask import Flask

from app.api.v1 import register_api_v1
from app.core.config import Settings, apply_settings_to_flask, get_settings
from app.core.extensions import init_extensions
from app.logging.logging_config import setup_bootstrap_logging, setup_logging
from app.middleware.rate_limit import register_rate_limiting


def create_app(
    *,
    settings: Settings | None = None,
    flask_config: Mapping[str, Any] | None = None,
) -> Flask:
    """Application factory function."""
    setup_bootstrap_logging()
    resolved_settings: Settings = settings or get_settings()
    app = Flask(__name__)
    setup_logging(app, resolved_settings)

    if flask_config:
        app.config.update(flask_config)

    apply_settings_to_flask(app, resolved_settings)
    init_extensions(app)
    register_api_v1(app)
    register_rate_limiting(app, resolved_settings)

    return app
