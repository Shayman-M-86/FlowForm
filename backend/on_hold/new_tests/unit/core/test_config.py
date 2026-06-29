"""Tests for FlowForm application configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from flask import Flask
from pydantic import SecretStr

from app.core.config import DatabaseSettings, Settings, apply_settings_to_flask


def _make_settings(
    secret_key_file: Path,
    core_database_url: str,
    response_database_url: str,
) -> Settings:
    """Build complete settings without depending on process environment."""
    return Settings.model_validate(
        {
            "flowform": {
                "env": "test",
                "app": {
                    "secret_key_file": str(secret_key_file),
                },
                "auth0": {
                    "domain": "flowform-test.auth0.com",
                    "audience": "https://api.flowform.test",
                    "client_id": "flowform-test-client",
                },
                "encryption": {
                    "kms_key_arn": "arn:aws:kms:ap-southeast-2:111122223333:key/test",
                    "linkage_secret_arn": "arn:aws:secretsmanager:ap-southeast-2:111122223333:secret:linkage",
                    "aws_region": "ap-southeast-2",
                    "aws_access_key_id": "test-access-key",
                    "aws_secret_access_key": "test-secret-access-key",
                },
            },
            "database": {
                "core": {"url": core_database_url},
                "response": {"url": response_database_url},
            },
        }
    )


def test_database_settings_accepts_full_url(core_database_url: str) -> None:
    """DatabaseSettings accepts a complete SQLAlchemy URL."""
    settings = DatabaseSettings.model_validate({"url": core_database_url})

    assert settings.url == core_database_url


def test_database_settings_builds_url_from_parts() -> None:
    """DatabaseSettings builds a SQLAlchemy URL from individual connection parts."""
    settings = DatabaseSettings(
        app_user="flowform_core_app",
        password=SecretStr("top-secret"),
        host="postgres-core",
        port=5432,
        name="flowform_core",
    )

    assert settings.url == "postgresql+psycopg://flowform_core_app:top-secret@postgres-core:5432/flowform_core"


def test_database_settings_loads_password_from_secret_file(tmp_path: Path) -> None:
    """DatabaseSettings reads the password from a mounted secret file when configured."""
    password_file = tmp_path / "db_password.txt"
    password_file.write_text("secret-from-file\n", encoding="utf-8")

    settings = DatabaseSettings(
        app_user="flowform_core_app",
        host="postgres-core",
        port=5432,
        name="flowform_core",
        app_password_file=str(password_file),
    )

    assert settings.password is not None
    assert settings.password.get_secret_value() == "secret-from-file"
    assert settings.url == "postgresql+psycopg://flowform_core_app:secret-from-file@postgres-core:5432/flowform_core"


def test_database_settings_rejects_missing_password_file(tmp_path: Path) -> None:
    """DatabaseSettings fails fast when a configured secret file does not exist."""
    with pytest.raises(ValueError, match="Database password file not found"):
        DatabaseSettings(
            app_user="flowform_core_app",
            host="postgres-core",
            port=5432,
            name="flowform_core",
            app_password_file=str(tmp_path / "missing.txt"),
        )


def test_database_settings_requires_url_or_complete_parts() -> None:
    """DatabaseSettings rejects partial connection settings."""
    with pytest.raises(ValueError, match=r"Provide either database\.url or all database parts"):
        DatabaseSettings(app_user="flowform_core_app", host="postgres-core")


def test_settings_loads_auth0_mgmt_from_flat_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Settings normalizes flat Auth0 management keys from environment variables."""
    secret_key_file = tmp_path / "secret-key.txt"
    core_password_file = tmp_path / "core-password.txt"
    response_password_file = tmp_path / "response-password.txt"
    secret_key_file.write_text("app-secret\n", encoding="utf-8")
    core_password_file.write_text("core-secret\n", encoding="utf-8")
    response_password_file.write_text("response-secret\n", encoding="utf-8")

    env = {
        "FLOWFORM_ENV": "dev",
        "FLOWFORM_APP_SECRET_KEY_FILE": str(secret_key_file),
        "FLOWFORM_AUTH0_DOMAIN": "example.auth0.com",
        "FLOWFORM_AUTH0_AUDIENCE": "https://api.example.test",
        "FLOWFORM_AUTH0_MGMT_ID": "management-client-id",
        "FLOWFORM_AUTH0_MGMT_SECRET": "management-client-secret",
        "FLOWFORM_ENCRYPTION_KMS_KEY_ARN": "arn:aws:kms:us-east-1:000:key/test",
        "FLOWFORM_ENCRYPTION_LINKAGE_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:000:secret:test",
        "FLOWFORM_ENCRYPTION_AWS_REGION": "us-east-1",
        "FLOWFORM_ENCRYPTION_AWS_ACCESS_KEY_ID": "test-access-key",
        "FLOWFORM_ENCRYPTION_AWS_SECRET_ACCESS_KEY": "test-secret-key",
        "DATABASE_CORE_APP_USER": "flowform_core_app",
        "DATABASE_CORE_HOST": "postgres-core",
        "DATABASE_CORE_NAME": "flowform_core",
        "DATABASE_CORE_APP_PASSWORD_FILE": str(core_password_file),
        "DATABASE_RESPONSE_APP_USER": "flowform_response_app",
        "DATABASE_RESPONSE_HOST": "postgres-response",
        "DATABASE_RESPONSE_NAME": "flowform_response",
        "DATABASE_RESPONSE_APP_PASSWORD_FILE": str(response_password_file),
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    settings = cast(Any, Settings)()

    assert settings.flowform.auth0.mgmt is not None
    assert settings.flowform.auth0.mgmt.id == "management-client-id"
    assert settings.flowform.auth0.mgmt.secret.get_secret_value() == "management-client-secret"
    assert settings.flowform.encryption.aws_region == "us-east-1"
    assert settings.database.core.password is not None
    assert settings.database.core.password.get_secret_value() == "core-secret"
    assert settings.database.response.password is not None
    assert settings.database.response.password.get_secret_value() == "response-secret"


def test_settings_apply_safe_defaults(
    secret_key_file: Path,
    core_database_url: str,
    response_database_url: str,
) -> None:
    """Optional settings groups should carry their default values."""
    settings = _make_settings(secret_key_file, core_database_url, response_database_url)

    assert settings.flowform.env == "test"
    assert settings.flowform.server.host == "127.0.0.1"
    assert settings.flowform.server.port == 5000
    assert settings.flowform.rate_limit.enabled is True
    assert settings.flowform.rate_limit.ignored_paths == ["/api/v1/system/health"]
    assert settings.flowform.logging.level == "INFO"


def test_apply_settings_to_flask_maps_runtime_config(
    secret_key_file: Path,
    core_database_url: str,
    response_database_url: str,
) -> None:
    """Loaded settings should be available through Flask config and extensions."""
    settings = _make_settings(secret_key_file, core_database_url, response_database_url)
    app = Flask(__name__)

    apply_settings_to_flask(app, settings)

    assert app.config["ENV_NAME"] == "test"
    assert app.config["TESTING"] is True
    assert app.config["SECRET_KEY"] == "test-secret-key"
    assert app.config["AUTH0_DOMAIN"] == settings.flowform.auth0.domain
    assert app.config["AUTH0_AUDIENCE"] == settings.flowform.auth0.audience
    assert app.config["HOST"] == "127.0.0.1"
    assert app.config["PORT"] == 5000
    assert app.extensions["settings"] is settings


def test_apply_settings_to_flask_can_be_called_directly(
    secret_key_file: Path,
    core_database_url: str,
    response_database_url: str,
) -> None:
    """Direct Flask mapping should not require the root app fixture."""
    settings = _make_settings(secret_key_file, core_database_url, response_database_url)
    flask_app = Flask(__name__)

    apply_settings_to_flask(flask_app, settings)

    assert flask_app.config["SECRET_KEY"] == "test-secret-key"
    assert flask_app.extensions["settings"] is settings
