import logging
from collections.abc import Mapping
from typing import Any

from flask import Flask

from app.api.v1 import register_api_v1
from app.core.config import Settings, apply_settings_to_flask, get_settings
from app.core.errors import ConfigError, InitializationError
from app.core.extensions import init_extensions
from app.core.register_options import openapi_register_options
from app.db.session import init_db_sessions
from app.logging.logging_config import setup_bootstrap_logging, setup_logging
from app.middleware.rate_limit import register_rate_limiting
from app.services.access.permissions_service import init_seed_data

logger = logging.getLogger(__name__)

# Exit code used when a catastrophic, non-recoverable boot error occurs
# (e.g. invalid configuration). Matches gunicorn's worker boot error code.
_BOOT_ERROR_EXIT_CODE = 3


def _log_fatal_boot_error(title: str, detail: str) -> None:
    """Log a clean, highly visible boot failure banner without a traceback.

    Catastrophic startup errors (invalid config, failed initialization) are
    caused by the deployment environment, not by a code bug, so a full Python
    traceback is noise. This prints just the actionable message inside a banner
    that is easy to spot in aggregated logs.
    """
    border = "=" * 72
    lines = [border, title, border, *detail.splitlines(), border]
    logger.critical("\n%s", "\n".join(lines))


def create_app(
    *,
    settings: Settings | None = None,
    flask_config: Mapping[str, Any] | None = None,
) -> Flask:
    """Application factory function."""
    setup_bootstrap_logging()
    try:
        resolved_settings: Settings = settings or get_settings()
        app = Flask(__name__)
        setup_logging(app, resolved_settings)

        if flask_config:
            app.config.update(flask_config)

        apply_settings_to_flask(app, resolved_settings)
        init_extensions(app)
        init_db_sessions(app)

        register_api_v1(app)
        register_rate_limiting(app, resolved_settings)

        from app.api.utils.errors import register_error_handlers

        register_error_handlers(app)

        openapi_register_options(app)

        import app.schema.orm as _  # noqa: F401 - Ensure models are registered with SQLAlchemy before migrations

        init_seed_data(app)
        return app
    except (ConfigError, InitializationError) as exc:
        # Non-recoverable, environment-caused boot failures: the message is
        # already actionable, so log a clean banner and exit without a
        # traceback rather than letting it propagate up through gunicorn.
        _log_fatal_boot_error("APPLICATION STARTUP FAILED", str(exc))
        raise SystemExit(_BOOT_ERROR_EXIT_CODE) from None
    except Exception:
        logger.exception("Application startup failed")
        raise
