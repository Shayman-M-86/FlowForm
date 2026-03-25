from pathlib import Path

import pytest
from pydantic import SecretStr

from app.core.config import DatabaseSettings


def test_database_settings_builds_url_from_parts() -> None:
    """DatabaseSettings builds a SQLAlchemy URL from individual connection parts."""
    settings = DatabaseSettings(
        user="flowform_core_app",
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

    settings = DatabaseSettings(
        user="flowform_core_app",
        host="postgres-core",
        port=5432,
        name="flowform_core",
        password_file=str(password_file),
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
            user="flowform_core_app",
            host="postgres-core",
            port=5432,
            name="flowform_core",
            password_file=str(tmp_path / "missing.txt"),
        )
