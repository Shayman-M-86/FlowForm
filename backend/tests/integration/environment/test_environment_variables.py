from helpers import read_env


def test_backend_env_override_ff_env() -> None:
    assert read_env("FF_ENV") == "test"


def test_backend_env_file_values_present() -> None:
    assert read_env("FF_PGDB_CORE__HOST") == "postgres-core"
    assert read_env("FF_PGDB_RESPONSE__HOST") == "postgres-response"


def test_backend_secret_file_vars_present() -> None:
    assert read_env("FF_PGDB_CORE__APP_PASSWORD_FILE") == "/run/secrets/FF_PGDB_CORE__APP_PASSWORD"
    assert read_env("FF_PGDB_RESPONSE__APP_PASSWORD_FILE") == "/run/secrets/FF_PGDB_RESPONSE__APP_PASSWORD"
