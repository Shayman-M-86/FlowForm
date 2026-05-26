import logging
from pathlib import Path
from typing import Any, cast

import pytest  # type: ignore[import]
from pydantic import SecretStr

from app.core.config import DatabaseSettings, Settings

logger = logging.getLogger("app.tests")


def test_database_settings_builds_url_from_parts() -> None:
    """DatabaseSettings builds a SQLAlchemy URL from individual connection parts."""
    settings = DatabaseSettings(
        app_user="flowform_core_app",
        password=SecretStr("top-secret"),
        host="postgres-core",
        port=5432,
        name="flowform_core",
    )

    assert (
        settings.url
        == "postgresql+psycopg://flowform_core_app:top-secret@postgres-core:5432/flowform_core"
    )


def test_database_settings_loads_password_from_secret_file(tmp_path: Path) -> None:
    """DatabaseSettings reads the password from a mounted secret file when configured."""
    password_file = tmp_path / "db_password.txt"
    password_file.write_text("secret-from-file\n", encoding="utf-8")
    logger.debug(
        f"Logging: Created temporary password file at {password_file}\033[0m"
    )
    settings = DatabaseSettings(
        app_user="flowform_core_app",
        host="postgres-core",
        port=5432,
        name="flowform_core",
        app_password_file=str(password_file),
    )

    assert settings.password is not None
    assert settings.password.get_secret_value() == "secret-from-file"
    assert (
        settings.url
        == "postgresql+psycopg://flowform_core_app:secret-from-file@postgres-core:5432/flowform_core"
    )


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


def test_settings_loads_auth0_mgmt_from_flat_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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
