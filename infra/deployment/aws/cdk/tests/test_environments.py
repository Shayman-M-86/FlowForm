from pathlib import Path

import pytest
from aws_cdk import RemovalPolicy
from aws_cdk import aws_logs as logs

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


def test_full_deployments_define_private_dns_and_flow_log_retention():
    staging = get_env_config("staging", env_dir=_EMPTY_ENV_DIR)
    prod = get_env_config("prod", env_dir=_EMPTY_ENV_DIR)

    assert staging.private_dns_zone == "internal.staging.flow-form.com.au"
    assert staging.vpc_flow_log_retention == logs.RetentionDays.ONE_WEEK
    assert prod.private_dns_zone == "internal.flow-form.com.au"
    assert prod.vpc_flow_log_retention == logs.RetentionDays.THREE_MONTHS


def test_database_lifecycle_and_capacity_are_environment_specific():
    staging = get_env_config("staging", env_dir=_EMPTY_ENV_DIR)
    prod = get_env_config("prod", env_dir=_EMPTY_ENV_DIR)

    assert staging.removal_policy == RemovalPolicy.DESTROY
    assert staging.database_removal_policy == RemovalPolicy.SNAPSHOT
    assert staging.db_allocated_storage_gib == 20
    assert staging.db_max_allocated_storage_gib == 40
    assert staging.db_backup_retention_days == 7

    assert prod.database_removal_policy == RemovalPolicy.RETAIN
    assert prod.db_instance_class == "db.t4g.small"
    assert prod.db_allocated_storage_gib == 20
    assert prod.db_max_allocated_storage_gib == 50
    assert prod.db_backup_retention_days == 30


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
