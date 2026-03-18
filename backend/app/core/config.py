from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Literal

from flask import current_app, Flask
from pydantic import BaseModel, SecretStr, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.error import ConfigError

logger = logging.getLogger(__name__)


class DatabaseSettings(BaseModel):
    url: str | None = None

    user: str | None = None
    host: str | None = None
    port: int | None = None
    name: str | None = None
    password: SecretStr | None = None
    scheme: str = "postgresql+psycopg"

    @model_validator(mode="after")
    def validate_and_build_url(self) -> DatabaseSettings:
        if self.url:
            return self

        required_parts = {
            "user": self.user,
            "password": self.password,
            "host": self.host,
            "port": self.port,
            "name": self.name,
        }

        missing = [key for key, value in required_parts.items() if value is None]
        if missing:
            raise ValueError(
                "Provide either database.url or all database parts. "
                f"Missing: {', '.join(missing)}"
            )

        assert self.password is not None

        self.url = (
            f"{self.scheme}://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.name}"
        )
        return self


class Auth0Settings(BaseModel):
    domain: str
    audience: str


class AppSettings(BaseModel):
    debug: bool = False
    secret_key: SecretStr


class LoggingSettings(BaseModel):
    level: str = "INFO"
    log_json: bool = False
    sqlalchemy_level: str = "WARNING"
    werkzeug_level: str = "INFO"
    log_file: str | None = None


class Settings(BaseSettings):
    env: Literal["dev", "test", "prod"]
    app: AppSettings
    database: DatabaseSettings
    auth0: Auth0Settings
    logging: LoggingSettings

    model_config = SettingsConfigDict(
        env_prefix="FLOWFORM_",
        env_nested_delimiter="__",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Get the application settings, loading them from the environment or .env files.

    Raises:
        ConfigError: If the configuration is invalid or missing required values.

    Returns:
        Settings: The application settings.
    """
    env_file_map = {
        "dev": ".env.dev",
        "test": ".env.test",
        "prod": ".env.prod",
    }

    env = os.getenv("FLOWFORM_ENV")
    try:
        if env is None:
            raise ConfigError("FLOWFORM_ENV is required")

        if env not in env_file_map:
            raise ConfigError("FLOWFORM_ENV must be one of: dev, test, prod")

        env_file = env_file_map[env]

        if env == "prod":
            settings = Settings()  # type: ignore[call-arg]
        else:
            settings = Settings(_env_file=env_file)  # type: ignore[call-arg]

        logger.info("Settings loaded for env=%s", settings.env)
        return settings

    except ValidationError as e:
        logger.critical("Invalid configuration", exc_info=e)
        raise ConfigError("Invalid application configuration") from e
    
    except ConfigError as e:
        logger.critical("Configuration error: %s", e)
        raise

def apply_settings_to_flask(app: Flask, settings: Settings) -> None:
    """Apply the given settings to the Flask app.

    Args:
        app (Flask): The Flask application instance.
        settings (Settings): The application settings.
    """
    mapping = {
        "ENV_NAME": settings.env,
        "DEBUG": settings.app.debug,
        "SECRET_KEY": settings.app.secret_key,
        "SQLALCHEMY_DATABASE_URI": settings.database.url,
        "AUTH0_DOMAIN": settings.auth0.domain,
        "AUTH0_AUDIENCE": settings.auth0.audience,
    }

    for key, value in mapping.items():
        if hasattr(value, "get_secret_value"):
            value = value.get_secret_value()
        app.config[key] = value
        
    app.extensions["settings"] = settings
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)


def current_settings() -> Settings:
    return current_app.extensions["settings"]