import logging

from app.core.config import Settings, get_settings
from tests.integration.environment.helpers import read_env

logger = logging.getLogger("app.tests.integration.environment.test_environment_variables")


def test_backend_env_override_flowform_env() -> None:
    assert read_env("FLOWFORM_ENV") == "test"


def test_backend_env_file_values_present() -> None:
    assert read_env("DATABASE_CORE_HOST") == "postgres-core"
    assert read_env("DATABASE_RESPONSE_HOST") == "postgres-response"


def test_backend_secret_file_vars_present() -> None:
    assert read_env("DATABASE_CORE_APP_PASSWORD_FILE") == "/run/secrets/DATABASE_CORE_APP_PASSWORD"
    assert read_env("DATABASE_RESPONSE_APP_PASSWORD_FILE") == "/run/secrets/DATABASE_RESPONSE_APP_PASSWORD"
    assert read_env("FLOWFORM_AUTH0_MGMT_SECRET_FILE") == "/run/secrets/FLOWFORM_AUTH0_MGMT_SECRET"


def test_environment_variables_from_settings() -> None:
    settings: Settings = get_settings()
    logger.info(
        "Core database settings loaded host=%s port=%s name=%s",
        settings.database.core.host,
        settings.database.core.port,
        settings.database.core.name,
    )

    assert settings.database.core.host == "postgres-core"
    assert settings.database.response.host == "postgres-response"


def test_response_database_environment_variables_from_settings() -> None:
    settings: Settings = get_settings()
    logger.info(
        "Response database settings loaded host=%s port=%s name=%s",
        settings.database.response.host,
        settings.database.response.port,
        settings.database.response.name,
    )

    assert settings.database.response.host == "postgres-response"
