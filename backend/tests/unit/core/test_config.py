import logging
import os
import tomllib
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest  # type: ignore[import]
from pydantic import SecretStr, ValidationError

from app.core import config as config_module
from app.core.config import (
    AppSettings,
    Auth0MgmtSettings,
    DatabaseSettings,
    FlowForm,
    Settings,
    TracingSettings,
)

logger = logging.getLogger("app.tests")


def test_tracing_settings_are_disabled_by_default() -> None:
    settings = TracingSettings()

    assert settings.enabled is False
    assert settings.otlp_endpoint == "http://alloy:4317"
    assert settings.sample_ratio == 1.0
    assert settings.service_name == "backend"


def _production_flowform(tmp_path: Path, origins: list[str]) -> dict[str, Any]:
    secret_key_file = tmp_path / "secret-key.txt"
    auth0_secret_file = tmp_path / "auth0-secret.txt"
    secret_key_file.write_text("app-secret\n", encoding="utf-8")
    auth0_secret_file.write_text("auth0-secret\n", encoding="utf-8")
    return {
        "env": "prod",
        "app": {"secret_key_file": str(secret_key_file)},
        "auth0": {
            "domain": "example.auth0.com",
            "audience": "https://api.example.test",
            "mgmt": {"id": "management-client-id", "secret_file": str(auth0_secret_file)},
        },
        "cors": {"origins": origins},
        "aws": {},
        "encryption": {
            "kms_key_arn": "arn:aws:kms:ap-southeast-2:000000000000:key/test",
            "linkage_secret_arn": "arn:aws:secretsmanager:ap-southeast-2:000000000000:secret:flowform/test/linkage",
        },
        "email": {"from_address": "no-reply@example.com"},
    }


@pytest.mark.parametrize("origins", [[], [""], ["*"]])
def test_production_rejects_empty_or_wildcard_cors_origins(tmp_path: Path, origins: list[str]) -> None:
    with pytest.raises(ValidationError):
        FlowForm.model_validate(_production_flowform(tmp_path, origins))


@pytest.mark.parametrize("origins", [[], [""], ["*"]])
def test_staging_rejects_empty_or_wildcard_cors_origins(tmp_path: Path, origins: list[str]) -> None:
    data = _production_flowform(tmp_path, origins)
    data["env"] = "staging"

    with pytest.raises(ValidationError):
        FlowForm.model_validate(data)


def test_staging_accepts_explicit_cors_origins(tmp_path: Path) -> None:
    data = _production_flowform(tmp_path, ["https://studio.staging.example.test"])
    data["env"] = "staging"

    settings = FlowForm.model_validate(data)

    assert settings.env == "staging"


def test_get_settings_accepts_staging_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = cast(Settings, SimpleNamespace(flowform=SimpleNamespace(env="staging")))
    monkeypatch.setenv("FLOWFORM_ENV", "staging")
    monkeypatch.setattr(config_module, "Settings", lambda: expected)
    config_module.get_settings.cache_clear()

    try:
        assert config_module.get_settings() is expected
    finally:
        config_module.get_settings.cache_clear()


def test_production_rejects_missing_cors_origins(tmp_path: Path) -> None:
    data = _production_flowform(tmp_path, ["https://studio.example.test"])
    data.pop("cors")
    with pytest.raises(ValidationError, match="FLOWFORM_CORS_ORIGINS"):
        FlowForm.model_validate(data)


def test_cors_origins_are_loaded_as_multiple_environment_values(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    secret_key_file = tmp_path / "secret-key.txt"
    core_password_file = tmp_path / "core-password.txt"
    response_password_file = tmp_path / "response-password.txt"
    for path in (secret_key_file, core_password_file, response_password_file):
        path.write_text("test-secret\n", encoding="utf-8")

    env = {
        "FLOWFORM_ENV": "test",
        "FLOWFORM_APP_SECRET_KEY_FILE": str(secret_key_file),
        "FLOWFORM_AUTH0_DOMAIN": "example.auth0.com",
        "FLOWFORM_AUTH0_AUDIENCE": "https://api.example.test",
        "FLOWFORM_AWS_ACCESS_KEY_ID": "test-access-key",
        "FLOWFORM_AWS_SECRET_ACCESS_KEY": "test-secret-key",
        "FLOWFORM_ENCRYPTION_KMS_KEY_ARN": "arn:aws:kms:ap-southeast-2:000000000000:key/test",
        "FLOWFORM_ENCRYPTION_LINKAGE_SECRET_ARN": (
            "arn:aws:secretsmanager:ap-southeast-2:000000000000:secret:flowform/test/linkage"
        ),
        "FLOWFORM_EMAIL_FROM_ADDRESS": "no-reply@example.com",
        "FLOWFORM_CORS_ORIGINS": '["https://studio.example.test", "https://site.example.test"]',
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
    assert settings.flowform.cors.origins == ["https://studio.example.test", "https://site.example.test"]


@pytest.mark.parametrize("sample_ratio", [-0.01, 1.01])
def test_tracing_settings_reject_invalid_sample_ratio(sample_ratio: float) -> None:
    with pytest.raises(ValidationError):
        TracingSettings(sample_ratio=sample_ratio)


def test_app_version_defaults_to_pyproject_version(tmp_path: Path) -> None:
    secret_key_file = tmp_path / "secret-key.txt"
    secret_key_file.write_text("app-secret\n", encoding="utf-8")
    pyproject = Path(__file__).resolve().parents[3] / "pyproject.toml"
    expected_version = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]

    settings = AppSettings(secret_key_file=str(secret_key_file))

    assert settings.version == expected_version


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
    logger.debug(f"Logging: Created temporary password file at {password_file}\033[0m")
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


def test_database_settings_iam_auth_builds_url_without_password() -> None:
    """IAM auth omits the password; the token is injected per connection."""
    settings = DatabaseSettings(
        auth_mode="iam",
        app_user="flowform_core_app",
        host="core.rds.example.test",
        port=5432,
        name="flowform_core",
    )

    assert settings.uses_iam_auth is True
    assert settings.password is None
    assert settings.url == "postgresql+psycopg://flowform_core_app@core.rds.example.test:5432/flowform_core"


def test_database_settings_iam_auth_rejects_static_password() -> None:
    """A static credential alongside IAM auth is a configuration error."""
    with pytest.raises(ValidationError, match="must not be set when database auth_mode is 'iam'"):
        DatabaseSettings(
            auth_mode="iam",
            app_user="flowform_core_app",
            host="core.rds.example.test",
            name="flowform_core",
            password=SecretStr("top-secret"),
        )


def test_database_settings_iam_auth_rejects_embedded_url() -> None:
    """An embedded URL would bypass the IAM token path entirely."""
    with pytest.raises(ValidationError, match="url must not be set when database auth_mode is 'iam'"):
        DatabaseSettings.model_validate(
            {
                "auth_mode": "iam",
                "url": "postgresql+psycopg://flowform_core_app:pw@core.rds.example.test:5432/flowform_core",
            }
        )


def test_database_settings_password_mode_still_requires_password() -> None:
    """Password mode keeps its existing requirement so dev/rehearsal are unchanged."""
    with pytest.raises(ValidationError, match="Missing: password"):
        DatabaseSettings(
            app_user="flowform_core_app",
            host="postgres-core",
            name="flowform_core",
        )


def _iam_database_parts() -> dict[str, Any]:
    return {
        "core": {
            "auth_mode": "iam",
            "app_user": "flowform_core_app",
            "host": "core.rds.example.test",
            "name": "flowform_core",
        },
        "response": {
            "auth_mode": "iam",
            "app_user": "flowform_response_app",
            "host": "response.rds.example.test",
            "name": "flowform_response",
        },
    }


@pytest.fixture
def _no_ambient_database_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drop DATABASE_* vars the test container sets.

    Settings is a BaseSettings, so model_validate still merges the process
    environment. The dev/test compose files export DATABASE_*_APP_PASSWORD_FILE,
    which would otherwise leak a static credential into these IAM cases.
    """
    for key in list(os.environ):
        if key.startswith("DATABASE_"):
            monkeypatch.delenv(key, raising=False)


@pytest.mark.usefixtures("_no_ambient_database_env")
def test_prod_allows_static_database_passwords(tmp_path: Path) -> None:
    """Prod may use password auth; the auth mode is chosen per deployment."""
    password_file = tmp_path / "core-password.txt"
    password_file.write_text("secret\n", encoding="utf-8")

    database = _iam_database_parts()
    database["core"] = {
        "app_user": "flowform_core_app",
        "host": "core.rds.example.test",
        "name": "flowform_core",
        "app_password_file": str(password_file),
    }

    settings = Settings.model_validate(
        {
            "flowform": _production_flowform(tmp_path, ["https://studio.example.test"]),
            "database": database,
        }
    )

    assert settings.database.core.uses_iam_auth is False
    assert settings.database.core.password is not None
    assert settings.database.core.password.get_secret_value() == "secret"
    assert settings.database.response.uses_iam_auth is True


@pytest.mark.usefixtures("_no_ambient_database_env")
def test_prod_accepts_iam_database_auth(tmp_path: Path) -> None:
    """A fully IAM-authenticated prod configuration validates."""
    settings = Settings.model_validate(
        {
            "flowform": _production_flowform(tmp_path, ["https://studio.example.test"]),
            "database": _iam_database_parts(),
        }
    )

    assert settings.database.core.uses_iam_auth is True
    assert settings.database.response.uses_iam_auth is True


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


def test_settings_accepts_direct_auth0_test_secret_without_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    secret_key_file = tmp_path / "secret-key.txt"
    core_password_file = tmp_path / "core-password.txt"
    response_password_file = tmp_path / "response-password.txt"
    secret_key_file.write_text("app-secret\n", encoding="utf-8")
    core_password_file.write_text("core-secret\n", encoding="utf-8")
    response_password_file.write_text("response-secret\n", encoding="utf-8")

    env = {
        "FLOWFORM_ENV": "test",
        "FLOWFORM_APP_SECRET_KEY_FILE": str(secret_key_file),
        "FLOWFORM_AUTH0_DOMAIN": "example.auth0.com",
        "FLOWFORM_AUTH0_AUDIENCE": "https://api.example.test",
        "FLOWFORM_AUTH0_MGMT_ID": "management-client-id",
        "FLOWFORM_AUTH0_MGMT_SECRET": "throwaway-management-client-secret",
        "FLOWFORM_AUTH0_MGMT_SECRET_FILE": "",
        "FLOWFORM_AUTH0_MGMT_VALIDATE_ON_STARTUP": "false",
        "FLOWFORM_AWS_ACCESS_KEY_ID": "test-access-key",
        "FLOWFORM_AWS_SECRET_ACCESS_KEY": "test-secret-key",
        "FLOWFORM_ENCRYPTION_KMS_KEY_ARN": "arn:aws:kms:ap-southeast-2:000000000000:key/test",
        "FLOWFORM_ENCRYPTION_LINKAGE_SECRET_ARN": (
            "arn:aws:secretsmanager:ap-southeast-2:000000000000:secret:flowform/test/linkage"
        ),
        "FLOWFORM_EMAIL_FROM_ADDRESS": "no-reply@example.com",
        "FLOWFORM_EMAIL_ENABLED": "false",
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
    assert settings.flowform.auth0.mgmt.secret.get_secret_value() == "throwaway-management-client-secret"
    assert settings.flowform.auth0.mgmt.validate_on_startup is False


def test_flowform_rejects_direct_auth0_secret_outside_test(tmp_path: Path) -> None:
    secret_key_file = tmp_path / "secret-key.txt"
    secret_key_file.write_text("app-secret\n", encoding="utf-8")

    with pytest.raises(
        ValidationError,
        match="FLOWFORM_AUTH0_MGMT_SECRET_FILE is required",
    ):
        FlowForm.model_validate(
            {
                "env": "dev",
                "app": {"secret_key_file": str(secret_key_file)},
                "auth0": {
                    "domain": "example.auth0.com",
                    "audience": "https://api.example.test",
                    "mgmt": {
                        "id": "management-client-id",
                        "secret": "direct-secret",
                    },
                },
                "aws": {},
                "encryption": {
                    "kms_key_arn": "arn:aws:kms:ap-southeast-2:000000000000:key/test",
                    "linkage_secret_arn": (
                        "arn:aws:secretsmanager:ap-southeast-2:000000000000:secret:flowform/test/linkage"
                    ),
                },
                "email": {"from_address": "no-reply@example.com"},
            }
        )


def test_flowform_prefers_auth0_secret_file_outside_test(tmp_path: Path) -> None:
    secret_key_file = tmp_path / "secret-key.txt"
    auth0_secret_file = tmp_path / "auth0-secret.txt"
    secret_key_file.write_text("app-secret\n", encoding="utf-8")
    auth0_secret_file.write_text("file-secret\n", encoding="utf-8")

    settings = FlowForm.model_validate(
        {
            "env": "dev",
            "app": {"secret_key_file": str(secret_key_file)},
            "auth0": {
                "domain": "example.auth0.com",
                "audience": "https://api.example.test",
                "mgmt": {
                    "id": "management-client-id",
                    "secret": "direct-secret-must-not-win",
                    "secret_file": str(auth0_secret_file),
                },
            },
            "aws": {},
            "encryption": {
                "kms_key_arn": "arn:aws:kms:ap-southeast-2:000000000000:key/test",
                "linkage_secret_arn": (
                    "arn:aws:secretsmanager:ap-southeast-2:000000000000:secret:flowform/test/linkage"
                ),
            },
            "email": {"from_address": "no-reply@example.com"},
        }
    )

    assert settings.auth0.mgmt is not None
    assert settings.auth0.mgmt.secret.get_secret_value() == "file-secret"


@pytest.mark.parametrize("environment", ["dev", "staging", "prod"])
def test_flowform_requires_auth0_startup_validation_outside_test(
    tmp_path: Path,
    environment: str,
) -> None:
    secret_key_file = tmp_path / "secret-key.txt"
    auth0_secret_file = tmp_path / "auth0-secret.txt"
    secret_key_file.write_text("app-secret\n", encoding="utf-8")
    auth0_secret_file.write_text("file-secret\n", encoding="utf-8")

    with pytest.raises(
        ValidationError,
        match="FLOWFORM_AUTH0_MGMT_VALIDATE_ON_STARTUP must be true",
    ):
        FlowForm.model_validate(
            {
                "env": environment,
                "app": {"secret_key_file": str(secret_key_file)},
                "auth0": {
                    "domain": "example.auth0.com",
                    "audience": "https://api.example.test",
                    "mgmt": {
                        "id": "management-client-id",
                        "secret_file": str(auth0_secret_file),
                        "validate_on_startup": False,
                    },
                },
                "aws": {},
                "encryption": {
                    "kms_key_arn": "arn:aws:kms:ap-southeast-2:000000000000:key/test",
                    "linkage_secret_arn": (
                        "arn:aws:secretsmanager:ap-southeast-2:000000000000:secret:flowform/test/linkage"
                    ),
                },
                "email": {"from_address": "no-reply@example.com"},
            }
        )


def test_auth0_mgmt_settings_loads_secret_from_file(tmp_path: Path) -> None:
    secret_file = tmp_path / "auth0-mgmt-secret.txt"
    secret_file.write_text("auth0-secret-from-file\n", encoding="utf-8")

    settings = Auth0MgmtSettings(
        id="management-client-id",
        secret_file=str(secret_file),
    )

    assert settings.secret.get_secret_value() == "auth0-secret-from-file"


def test_auth0_mgmt_settings_rejects_missing_secret_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Auth0 management secret file not found"):
        Auth0MgmtSettings(
            id="management-client-id",
            secret_file=str(tmp_path / "missing.txt"),
        )
