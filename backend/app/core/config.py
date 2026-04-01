from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, cast

from flask import Flask, current_app
from pydantic import BaseModel, Field, SecretStr, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.error import ConfigError

logger = logging.getLogger(__name__)


class DatabaseSettings(BaseModel):
    """Database connection settings for the application."""

    url: str | None = None

    app_user: str | None = None
    host: str | None = None
    port: int | None = 5432
    name: str | None = None
    password: SecretStr | None = None
    app_password_file: str | None = None
    scheme: str = "postgresql+psycopg"

    @model_validator(mode="after")
    def load_password_from_file(self) -> DatabaseSettings:
        """Load the database password from a mounted secret file when provided.

        Raises:
            ValueError: If the password file is not found.
        """
        if self.password is not None or self.app_password_file is None:
            return self

        password_path = Path(self.app_password_file)
        if not password_path.is_file():
            raise ValueError(f"Database password file not found: {self.app_password_file}")

        self.password = SecretStr(password_path.read_text(encoding="utf-8").strip())
        return self

    @model_validator(mode="after")
    def validate_and_build_url(self) -> DatabaseSettings:
        """Build a database URL from individual parts when ``url`` is not set.

        Raises:
            ValueError: If required connection parts are missing.
        """
        if self.url:
            return self

        required_parts = {
            "app_user": self.app_user,
            "password": self.password,
            "host": self.host,
            "port": self.port,
            "name": self.name,
        }

        missing = [key for key, value in required_parts.items() if value is None]
        if missing:
            raise ValueError(
                f"Provide either database.url or all database parts. Missing: {', '.join(missing)}"
            )

        self.url = (
            f"{self.scheme}://{self.app_user}:{self.password.get_secret_value()}"  # type: ignore
            f"@{self.host}:{self.port}/{self.name}"
        )
        return self


class ServerSettings(BaseModel):
    """Server host and port settings."""

    host: str = "127.0.0.1"
    port: int = 5000


class Auth0Settings(BaseModel):
    """Auth0 configuration for authentication and authorization."""

    domain: str
    audience: str


class AppSettings(BaseModel):
    """High-level application behavior settings."""

    debug: bool = False
    secret_key: SecretStr | None = None
    secret_key_file: str 

    @model_validator(mode="after")
    def load_secret_key_from_file(self) -> AppSettings:
        """Load the Flask secret key from a mounted secret file when provided.

        Raises:
            ValueError: If the secret key file is not found.
        """
        secret_key_path = Path(self.secret_key_file)
        logger.critical(f"Loading secret key from file: {secret_key_path}")
        logger.critical(f"Secret key file exists: {secret_key_path.is_file()}")
        logger.critical(
            f"Secret key file content preview: {secret_key_path.read_text(encoding='utf-8').strip()[:10]}..."
        )  # type: ignore
        if not secret_key_path.is_file():
            raise ValueError(f"Secret key file not found: {self.secret_key_file}")

        self.secret_key = SecretStr(secret_key_path.read_text(encoding="utf-8").strip())
        return self


class RateLimitSettings(BaseModel):
    """Global rate limiting configuration."""

    enabled: bool = True
    max_requests: int = 20
    window_seconds: int = 5
    ignored_paths: list[str] = Field(default_factory=lambda: ["/api/v1/health"])


class LoggingSettings(BaseModel):
    """Logging configuration for the application and dependencies."""

    level: str = "INFO"
    log_json: bool = False
    sqlalchemy_level: str = "WARNING"
    werkzeug_level: str = "WARNING"
    log_file: str | None = None
    log_file_backup_count: int = 5
    log_file_max_bytes: int = 5 * 1024 * 1024  # 5 MB
    requests: bool = True  # Whether to log HTTP requests
    duration: bool = False  # Whether to log request duration

class FlowForm(BaseModel):
    """Top-level application settings loaded from environment variables."""

    env: Literal["dev", "test", "prod"]
    app: AppSettings
    auth0: Auth0Settings
    server: ServerSettings = Field(default_factory=ServerSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

class DataBase(BaseModel):
    """Database configuration for the application."""

    core: DatabaseSettings = Field(default_factory=DatabaseSettings)
    response: DatabaseSettings = Field(default_factory=DatabaseSettings)

class Settings(BaseSettings):
    """Top-level application settings loaded from environment variables."""

    flowform: FlowForm
    database: DataBase



    model_config = SettingsConfigDict(
        env_nested_delimiter="_",
        env_nested_max_split=2,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Load application settings from environment variables.

    Raises:
        ConfigError: If configuration is invalid or the environment name is unsupported.

    Returns:
        Loaded application settings.
    """
    env = os.getenv("FLOWFORM_ENV")
    # try:
    if env is None:
        raise ConfigError(
            "FLOWFORM_ENV is required and must be one of: dev, test, prod. "
            "This should be provided by the container environment."
        )

    env = env.lower()
    if env not in {"dev", "test", "prod"}:
        raise ConfigError("FLOWFORM_ENV must be one of: dev, test, prod")

    logger.info("Loading settings for env=%s from environment variables", env)
    settings = cast(Any, Settings)()

    logger.info("Settings loaded for env=%s", settings.flowform.env)
    return settings

    # except ValidationError as exc:
    #     logger.critical("Configuration error: %s", exc)
    #     raise ConfigError(f"Invalid application configuration {exc}") from exc

    # except ConfigError as exc:
    #     logger.critical("Configuration error: %s", exc)
    #     raise


def apply_settings_to_flask(app: Flask, settings: Settings) -> None:
    """Apply loaded settings to a Flask application.

    Args:
        app: Flask application instance.
        settings: Application settings to apply.
    """
    mapping = {
        "ENV_NAME": settings.flowform.env,
        "DEBUG": settings.flowform.app.debug,
        "SECRET_KEY": settings.flowform.app.secret_key,
        "SQLALCHEMY_DATABASE_URI": settings.database.core.url,
        "AUTH0_DOMAIN": settings.flowform.auth0.domain,
        "AUTH0_AUDIENCE": settings.flowform.auth0.audience,
        "HOST": settings.flowform.server.host,
        "PORT": settings.flowform.server.port,
        "TESTING": settings.flowform.env == "test",
    }

    for key, value in mapping.items():
        if isinstance(value, SecretStr):
            value = value.get_secret_value()
        app.config[key] = value

    if settings.database.response and settings.database.response.url:
        app.config["SQLALCHEMY_BINDS"] = {"response": settings.database.response.url}

    app.extensions["settings"] = settings
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    logger.info(f"SQLALCHEMY_BINDS: {app.config.get('SQLALCHEMY_BINDS')}")


def current_settings() -> Settings:
    """Return the current application settings from the Flask context."""
    return current_app.extensions["settings"]
