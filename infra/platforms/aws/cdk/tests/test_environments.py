from pathlib import Path

import pytest

from flowform_infra.config import get_env_config

_EMPTY_ENV_DIR = Path(__file__).parent  # no .env.* files here


def _write_env_file(tmp_path: Path, env_name: str, content: str) -> Path:
    (tmp_path / f".env.{env_name}").write_text(content)
    return tmp_path


def test_unknown_env_raises():
    with pytest.raises(ValueError, match="Unknown env"):
        get_env_config("qa")


def test_dev_is_not_full_deployment():
    assert get_env_config("dev", env_dir=_EMPTY_ENV_DIR).full_deployment is False


def test_auth0_public_none_without_env_file():
    assert get_env_config("staging", env_dir=_EMPTY_ENV_DIR).auth0_public is None


def test_auth0_public_loaded_from_env_file(tmp_path):
    env_dir = _write_env_file(
        tmp_path,
        "staging",
        "# comment line\n"
        "AUTH0_DOMAIN=auth.example.com\n"
        "AUTH0_CLIENT_ID=abc123\n"
        "AUTH0_AUDIENCE=https://example.auth.api\n"
        "APP_SECRET_KEY=ignored-by-loader\n",
    )
    auth0 = get_env_config("staging", env_dir=env_dir).auth0_public
    assert auth0 is not None
    assert auth0.domain == "auth.example.com"
    assert auth0.client_id == "abc123"
    assert auth0.audience == "https://example.auth.api"


def test_auth0_public_none_when_env_file_incomplete(tmp_path):
    env_dir = _write_env_file(tmp_path, "staging", "AUTH0_DOMAIN=auth.example.com\n")
    assert get_env_config("staging", env_dir=env_dir).auth0_public is None
