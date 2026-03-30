import logging

from helpers import read_env

from app.core.config import Settings, get_settings

logger = logging.getLogger("app.tests.integration.environment.test_environment_variables")


def test_backend_env_override_ff_env() -> None:
    assert read_env("FF_ENV") == "test"


def test_backend_env_file_values_present() -> None:
    assert read_env("FF_PGDB_CORE__HOST") == "postgres-core"
    assert read_env("FF_PGDB_RESPONSE__HOST") == "postgres-response"


def test_backend_secret_file_vars_present() -> None:
    assert read_env("FF_PGDB_CORE__APP_PASSWORD_FILE") == "/run/secrets/FF_PGDB_CORE__APP_PASSWORD"
    assert read_env("FF_PGDB_RESPONSE__APP_PASSWORD_FILE") == "/run/secrets/FF_PGDB_RESPONSE__APP_PASSWORD"


def test_environment_variables_from_settings() -> None:
    settings: Settings = get_settings()
    url = settings.pgdb_core.url
    logger.info(f"Constructed database URL from settings: {url}")

    assert settings.pgdb_core.host == "postgres-core"
    assert settings.pgdb_response.host == "postgres-response"

def test_response_database_environment_variables_from_settings() -> None:
    settings: Settings = get_settings()
    url = settings.pgdb_response.url
    logger.info(f"Constructed response database URL from settings: {url}")

    assert settings.pgdb_response.host == "postgres-response"
