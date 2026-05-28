from flask import Flask


def openapi_register_options(app: Flask) -> None:
    """Register OpenAPI routes + CLI in non-prod environments.

    Called during ``create_app`` while the Flask app is still being built,
    so we can't use ``current_app`` / ``current_settings`` — those need an
    active app context. Read ``ENV_NAME`` directly from the config that
    ``apply_settings_to_flask`` just populated.
    """
    if app.config.get("ENV_NAME") in {"dev", "test"}:
        from app.openapi import register_openapi_blueprint, register_openapi_cli

        register_openapi_blueprint(app)
        register_openapi_cli(app)
