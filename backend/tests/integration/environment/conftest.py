from __future__ import annotations

import logging
import time
from pathlib import Path

import pytest
from helpers import current_database_name, read_env

logger = logging.getLogger("app.tests.integration.environment")

REQUIRED_ENV_VARS = (
    "FLOWFORM_ENV",
    "DATABASE_CORE_HOST",
    "DATABASE_CORE_PORT",
    "DATABASE_CORE_NAME",
    "DATABASE_CORE_APP_USER",
    "DATABASE_CORE_APP_PASSWORD_FILE",
    "DATABASE_RESPONSE_HOST",
    "DATABASE_RESPONSE_PORT",
    "DATABASE_RESPONSE_NAME",
    "DATABASE_RESPONSE_APP_USER",
    "DATABASE_RESPONSE_APP_PASSWORD_FILE",
)


def pytest_configure() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


@pytest.fixture(scope="session", autouse=True)
def validate_test_environment() -> None:
    missing = [name for name in REQUIRED_ENV_VARS if not read_env(name, required=False)]
    if missing:
        pytest.exit(
            f"Integration tests must run inside the backend test container.\nMissing env vars: {', '.join(missing)}",
            returncode=1,
        )

    for env_name in ("DATABASE_CORE_APP_PASSWORD_FILE", "DATABASE_RESPONSE_APP_PASSWORD_FILE"):
        secret_path = Path(read_env(env_name))
        if not secret_path.is_file():
            pytest.exit(
                f"Expected mounted secret file for {env_name}: {secret_path}",
                returncode=1,
            )


@pytest.fixture(scope="session", autouse=True)
def wait_for_databases() -> None:
    for prefix in ("DATABASE_CORE", "DATABASE_RESPONSE"):
        _wait_for_database(prefix)


def _wait_for_database(prefix: str, timeout: float = 30.0, interval: float = 1.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            current_database_name(prefix)
            logger.info("%s is reachable", prefix)
            return
        except Exception as exc:
            last_error = exc
            time.sleep(interval)

    pytest.exit(
        f"Timed out waiting for {prefix} to become reachable.\nLast error: {last_error}",
        returncode=1,
    )
