from __future__ import annotations

import logging
import os
import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, cast

from flask import Flask, current_app
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    SecretStr,
    ValidationError,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic.networks import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.errors import ConfigError

logger = logging.getLogger(__name__)

_PYPROJECT_PATH = Path(__file__).resolve().parents[2] / "pyproject.toml"


def _load_project_version() -> str:
    """Load the backend version declared in pyproject.toml."""
    try:
        project = tomllib.loads(_PYPROJECT_PATH.read_text(encoding="utf-8"))["project"]
        version = project["version"]
    except (KeyError, OSError, tomllib.TOMLDecodeError) as exc:
        raise RuntimeError(f"Unable to load backend version from {_PYPROJECT_PATH}") from exc

    if not isinstance(version, str) or not version:
        raise RuntimeError(f"Invalid backend version in {_PYPROJECT_PATH}")
    return version


PROJECT_VERSION = _load_project_version()


def _load_secret_from_file(secret_file: str, *, label: str) -> SecretStr:
    """Load a secret value from a mounted secret file."""
    secret_path = Path(secret_file)
    if not secret_path.is_file():
        raise ValueError(f"{label} file not found: {secret_file}")

    return SecretStr(secret_path.read_text(encoding="utf-8").strip())


class DatabaseSettings(BaseModel):
    """Database connection settings for the application."""

    url_value: PostgresDsn | None = Field(default=None, validation_alias="url")

    app_user: str | None = None
    host: str | None = None
    port: int = 5432
    name: str | None = None
    password: SecretStr | None = None
    app_password_file: str | None = None
    scheme: str = "postgresql+psycopg"

    @model_validator(mode="after")
    def load_password_from_file(self) -> DatabaseSettings:
        """Load the database password from a mounted secret file when provided."""
        if self.password is not None or self.app_password_file is None:
            return self

        self.password = _load_secret_from_file(
            self.app_password_file,
            label="Database password",
        )
        return self

    @model_validator(mode="after")
    def validate_database_config(self) -> DatabaseSettings:
        """Require either a full URL or all URL parts."""
        if self.url_value is not None:
            return self

        required_parts = {
            "app_user": self.app_user,
            "password": self.password,
            "host": self.host,
            "name": self.name,
        }

        missing = [key for key, value in required_parts.items() if value is None]
        if missing:
            raise ValueError(f"Provide either database.url or all database parts. Missing: {', '.join(missing)}")

        return self

    @computed_field
    @property
    def dsn_url(self) -> PostgresDsn:
        """Return the final validated database URL."""
        if self.url_value is not None:
            return self.url_value

        return PostgresDsn(
            f"{self.scheme}://"
            f"{self.app_user}:{self.password.get_secret_value()}"  # type: ignore
            f"@{self.host}:{self.port}/{self.name}"
        )

    @property
    def url(self) -> str:
        return str(self.dsn_url)


class AwsSettings(BaseModel):
    """Shared AWS runtime settings used by app services."""

    region: str = "ap-southeast-2"

    access_key_id: SecretStr | None = None
    secret_access_key: SecretStr | None = None


class EmailSettings(BaseModel):
    """Email delivery settings for AWS SES."""

    from_address: EmailStr
    from_name: str = "FlowForm"
    reply_to_address: EmailStr | None = None

    configuration_set_name: str | None = None
    enabled: bool = True

    recipient_cooldown_seconds: int = 3600
    global_rate_limit: int = 50
    global_rate_window_seconds: int = 60


class ServerSettings(BaseModel):
    """Server host and port settings."""

    host: str = "127.0.0.1"
    port: int = 5000
    site_url: str = "http://localhost:5174"


class CorsSettings(BaseModel):
    """Browser cross-origin policy for API routes."""

    origins: list[str] = Field(default_factory=list)
    supports_credentials: bool = True

    @field_validator("origins")
    @classmethod
    def normalize_origins(cls, origins: list[str]) -> list[str]:
        """Reject empty origin entries and normalize surrounding whitespace."""
        normalized = [origin.strip() for origin in origins if origin.strip()]
        if len(normalized) != len(origins):
            raise ValueError("origins must not contain empty entries")
        return normalized


class Auth0MgmtSettings(BaseModel):
    """Auth0 Management API credentials for user and role management."""

    id: str
    secret: SecretStr
    secret_file: str | None = None
    # Canonical tenant domain (e.g. dev-xxx.au.auth0.com) for the Management
    # API. Auth0 does NOT serve /api/v2 on custom domains — requesting a token
    # for https://<custom-domain>/api/v2/ fails with "Service not enabled
    # within domain". When the login/issuer domain is a custom domain, set this
    # to the canonical tenant so the mgmt client uses it. Falls back to the
    # issuer domain when unset (tenants without a custom domain).
    domain: str | None = None
    validate_on_startup: bool = True

    def __init__(
        self,
        *,
        id: str,
        secret: SecretStr | str | None = None,
        secret_file: str | None = None,
        domain: str | None = None,
        validate_on_startup: bool = True,
    ) -> None:
        data: dict[str, Any] = {
            "id": id,
            "secret_file": secret_file,
            "domain": domain,
            "validate_on_startup": validate_on_startup,
        }
        if secret is not None:
            data["secret"] = secret
        super().__init__(**data)

    @model_validator(mode="before")
    @classmethod
    def load_secret_from_file(cls, data: Any) -> Any:
        """Prefer a configured mounted secret file over a direct secret."""
        if not isinstance(data, dict):
            return data

        secret_file = data.get("secret_file")
        if not secret_file:
            return data

        return {
            **data,
            "secret": _load_secret_from_file(
                str(secret_file),
                label="Auth0 management secret",
            ),
        }


class Auth0Settings(BaseModel):
    """Auth0 configuration for authentication and authorization."""

    domain: str
    audience: str
    client_id: str | None = None
    mgmt: Auth0MgmtSettings | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_mgmt_env_keys(cls, data: Any) -> Any:
        if not isinstance(data, dict) or data.get("mgmt") is not None:
            return data

        mgmt_id = data.get("mgmt_id")
        mgmt_secret = data.get("mgmt_secret")
        mgmt_secret_file = data.get("mgmt_secret_file")
        mgmt_domain = data.get("mgmt_domain")
        mgmt_validate_on_startup = data.get("mgmt_validate_on_startup", True)
        if mgmt_id is None and mgmt_secret is None and mgmt_secret_file is None:
            return data

        return {
            **data,
            "mgmt": {
                "id": mgmt_id,
                "secret": mgmt_secret,
                "secret_file": mgmt_secret_file,
                "domain": mgmt_domain,
                "validate_on_startup": mgmt_validate_on_startup,
            },
        }


class AppSettings(BaseModel):
    """High-level application behavior settings."""

    version: str = PROJECT_VERSION
    debug: bool = False
    secret_key: SecretStr | None = None
    secret_key_file: str

    @model_validator(mode="after")
    def load_secret_key_from_file(self) -> AppSettings:
        """Load the Flask secret key from a mounted secret file when provided.

        Raises:
            ValueError: If the secret key file is not found.
        """
        self.secret_key = _load_secret_from_file(
            self.secret_key_file,
            label="Secret key",
        )
        return self


class EncryptionSettings(BaseModel):
    """AWS encryption settings for session response encryption."""

    # KMS key used to wrap/unwrap per-session DEKs
    kms_key_arn: str

    # Secrets Manager secret holding versioned linkage keys as JSON:
    # {"version": N, "secret_b64": "..."}. AWSCURRENT stage = active key.
    linkage_secret_arn: str

    # How long (seconds) to cache linkage keys in memory before re-fetching
    linkage_key_cache_ttl_seconds: float = 1800.0
    key_cache_enabled: bool = True


class RateLimitSettings(BaseModel):
    """Global rate limiting configuration."""

    enabled: bool = True
    max_requests: int = 30
    window_seconds: int = 5
    ignored_paths: list[str] = Field(default_factory=lambda: ["/api/v1/system/health"])


class LoggingSettings(BaseModel):
    """Logging configuration for the application and dependencies."""

    level: str = "INFO"
    log_json: bool = False
    sqlalchemy_level: str = "WARNING"
    werkzeug_level: str = "WARNING"
    log_file: str | None = None
    log_file_backup_count: int = 2
    log_file_max_bytes: int = 5 * 1024 * 1024  # 5 MB
    requests: bool = True  # Whether to log HTTP requests
    duration: bool = False  # Whether to log request duration


class TracingSettings(BaseModel):
    """OpenTelemetry trace export settings."""

    enabled: bool = False
    otlp_endpoint: str = "http://alloy:4317"
    sample_ratio: float = Field(default=1.0, ge=0.0, le=1.0)
    service_name: str = Field(default="backend", min_length=1)

    defer_provider: bool = False
    """Delay tracer-provider creation until after Gunicorn forks its workers.

    The batch span processor owns a background thread that must be created in
    each worker, not inherited across a fork. Gunicorn's config sets
    ``FLOWFORM_TRACING_DEFER_PROVIDER=true`` before boot so ``configure_tracing``
    skips provider setup and ``post_fork`` initializes it per worker instead.
    """


class FlowForm(BaseModel):
    """Top-level application settings loaded from environment variables."""

    env: Literal["dev", "test", "prod"]
    app: AppSettings
    auth0: Auth0Settings
    server: ServerSettings = Field(default_factory=ServerSettings)
    cors: CorsSettings = Field(default_factory=CorsSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    tracing: TracingSettings = Field(default_factory=TracingSettings)
    aws: AwsSettings
    encryption: EncryptionSettings
    email: EmailSettings

    @model_validator(mode="after")
    def validate_auth0_mgmt_secret_source(self) -> FlowForm:
        """Require file-backed Auth0 management credentials outside tests."""
        if self.env == "test":
            return self

        mgmt = self.auth0.mgmt
        if mgmt is None or not mgmt.secret_file:
            raise ValueError("FLOWFORM_AUTH0_MGMT_SECRET_FILE is required when FLOWFORM_ENV is dev or prod")
        if not mgmt.validate_on_startup:
            raise ValueError("FLOWFORM_AUTH0_MGMT_VALIDATE_ON_STARTUP must be true when FLOWFORM_ENV is dev or prod")

        return self

    @model_validator(mode="after")
    def validate_cors_settings(self) -> FlowForm:
        """Fail closed for production browser-origin settings."""
        if self.env != "prod":
            return self

        if not self.cors.origins:
            raise ValueError(
                "FLOWFORM_CORS_ORIGINS must contain at least one explicit origin when FLOWFORM_ENV is prod"
            )
        if self.cors.supports_credentials and "*" in self.cors.origins:
            raise ValueError("FLOWFORM_CORS_ORIGINS must not contain '*' when credentials are enabled in production")
        return self


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


def _loc_to_path(loc: tuple[str | int, ...]) -> str:
    """Convert a Pydantic error location to a readable dot path."""
    path = ""

    for i, part in enumerate(loc):
        if isinstance(part, str):
            if i > 0:
                path += "."
            path += part
        else:
            path += f"[{part}]"

    return path


def _loc_to_env_var(loc: tuple[str | int, ...]) -> str | None:
    """Best-effort conversion of a nested location to its env var name."""
    parts = [part.upper() for part in loc if isinstance(part, str)]
    if not parts:
        return None
    return "_".join(parts)


def _format_settings_validation_error(exc: ValidationError) -> str:
    """Format settings validation errors into a clearer multi-line message."""
    lines = ["Invalid application configuration:"]

    for error in exc.errors():
        loc = tuple(error.get("loc", ()))
        path = _loc_to_path(loc)
        env_var = _loc_to_env_var(loc)
        msg = error.get("msg", "Invalid value")

        if env_var:
            lines.append(f"- {path}: {msg} (env: {env_var})")
        else:
            lines.append(f"- {path}: {msg}")

    return "\n".join(lines)


@lru_cache
def get_settings() -> Settings:
    """Load application settings from environment variables."""
    env = os.getenv("FLOWFORM_ENV")

    if env is None:
        raise ConfigError(
            "FLOWFORM_ENV is required and must be one of: dev, test, prod. "
            "This should be provided by the container environment."
        )

    env = env.lower()
    if env not in {"dev", "test", "prod"}:
        raise ConfigError("FLOWFORM_ENV must be one of: dev, test, prod")

    logger.info("Loading settings for env=%s from environment variables", env)

    try:
        settings = cast(Any, Settings)()
    except ValidationError as exc:
        formatted = _format_settings_validation_error(exc)
        raise ConfigError(formatted) from exc

    logger.info("Settings loaded for env=%s", settings.flowform.env)
    return settings


def apply_settings_to_flask(app: Flask, settings: Settings) -> None:
    """Apply loaded settings to a Flask application."""
    mapping = {
        "ENV_NAME": settings.flowform.env,
        "APP_VERSION": settings.flowform.app.version,
        "DEBUG": settings.flowform.app.debug,
        "SECRET_KEY": settings.flowform.app.secret_key,
        "AUTH0_DOMAIN": settings.flowform.auth0.domain,
        "AUTH0_AUDIENCE": settings.flowform.auth0.audience,
        "AUTH0_CLIENT_ID": settings.flowform.auth0.client_id,
        "HOST": settings.flowform.server.host,
        "PORT": settings.flowform.server.port,
        "TESTING": settings.flowform.env == "test",
    }

    for key, value in mapping.items():
        if isinstance(value, SecretStr):
            value = value.get_secret_value()
        app.config[key] = value

    app.extensions["settings"] = settings


def current_settings() -> Settings:
    """Return the current application settings from the Flask context."""
    return current_app.extensions["settings"]
