import json
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

from flowform_infra.database_bootstrap.bootstrap import handler as handler_module
from flowform_infra.database_bootstrap.bootstrap.models import (
    BootstrapPhase,
    BootstrapRequest,
    DatabaseCredentials,
)
from flowform_infra.database_bootstrap.bootstrap.postgres import (
    _requires_schema_load,
)
from flowform_infra.database_bootstrap.bootstrap.services import SqlRepository

CHECKSUM = "a" * 64
DATABASE_INIT_DIR = Path(__file__).parents[5] / "infra" / "database" / "init"


def _configure_handler_environment(monkeypatch):
    monkeypatch.setenv("BOOTSTRAP_VERSION", "3")
    monkeypatch.setenv("BOOTSTRAP_CHECKSUM", CHECKSUM)
    monkeypatch.setenv("DATABASE_SECRET_ARN", "database-secret")
    monkeypatch.setenv("DATABASE_HOST", "database.internal")
    monkeypatch.setenv("DATABASE_PORT", "5432")
    monkeypatch.setenv("FLOWFORM_ENVIRONMENT", "staging")
    monkeypatch.setattr(handler_module.boto3, "client", lambda _service: object())


def test_handler_operation_id_falls_back_to_the_lambda_request():
    assert handler_module._operation_id({}, "request-123") == "lambda-request-123"


def test_handler_emits_correlated_structured_success_log(monkeypatch, caplog):
    class CredentialProvider:
        def __init__(self, *_args, **_kwargs):
            pass

        def load(self):
            return object()

    class Bootstrapper:
        def __init__(self, **_kwargs):
            self.phase = BootstrapPhase.CONNECT

        def run(self, _request):
            self.phase = BootstrapPhase.COMPLETE

    _configure_handler_environment(monkeypatch)
    monkeypatch.setattr(handler_module, "SecretsManagerCredentialProvider", CredentialProvider)
    monkeypatch.setattr(handler_module, "PostgresConnector", lambda _credentials: object())
    monkeypatch.setattr(handler_module, "SqlRepository", lambda: object())
    monkeypatch.setattr(handler_module, "PostgresBootstrapper", Bootstrapper)
    monotonic_values = iter((100.0, 100.125))
    monkeypatch.setattr(handler_module.time, "monotonic", lambda: next(monotonic_values))
    caplog.set_level(logging.INFO)

    result = handler_module.handler(
        {
            "BootstrapVersion": "3",
            "BootstrapChecksum": CHECKSUM,
            "OperationId": "staging-deploy-123",
        },
        SimpleNamespace(aws_request_id="lambda-request-123"),
    )

    assert result == {
        "Succeeded": True,
        "BootstrapVersion": "3",
        "BootstrapChecksum": CHECKSUM,
    }
    completed = next(record for record in caplog.records if record.message == "database_bootstrap.completed")
    assert completed.operation_id == "staging-deploy-123"
    assert completed.environment == "staging"
    assert completed.lambda_request_id == "lambda-request-123"
    assert completed.component == "database-bootstrap"
    assert completed.phase == "complete"
    assert completed.outcome == "succeeded"
    assert completed.duration_ms == 125
    assert completed.bootstrap_version == "3"
    assert completed.bootstrap_checksum == CHECKSUM


def test_handler_suppresses_external_failure_details(monkeypatch, caplog):
    class ExternalServiceFailure(Exception):
        pass

    class CredentialProvider:
        def __init__(self, *_args, **_kwargs):
            pass

        def load(self):
            raise ExternalServiceFailure("do-not-log-this-secret")

    _configure_handler_environment(monkeypatch)
    monkeypatch.setattr(handler_module, "SecretsManagerCredentialProvider", CredentialProvider)
    monotonic_values = iter((100.0, 100.25))
    monkeypatch.setattr(handler_module.time, "monotonic", lambda: next(monotonic_values))
    caplog.set_level(logging.INFO)

    result = handler_module.handler(
        {
            "BootstrapVersion": "3",
            "BootstrapChecksum": CHECKSUM,
            "OperationId": "staging-deploy-456",
        },
        SimpleNamespace(aws_request_id="lambda-request-456"),
    )

    assert result == {
        "Succeeded": False,
        "ErrorCode": "ExternalServiceFailure",
        "ErrorMessage": "Database bootstrap failed during load_secret.",
    }
    failed = next(record for record in caplog.records if record.message == "database_bootstrap.failed")
    assert failed.operation_id == "staging-deploy-456"
    assert failed.phase == "load_secret"
    assert failed.outcome == "failed"
    assert failed.duration_ms == 250
    assert failed.error_code == "ExternalServiceFailure"
    assert failed.error_detail == "detail suppressed"
    assert "do-not-log-this-secret" not in caplog.text


def test_bootstrap_request_accepts_the_deployed_version_identity():
    request = BootstrapRequest.from_event(
        {
            "BootstrapVersion": "1",
            "BootstrapChecksum": CHECKSUM,
        }
    )

    request.require_expected(version="1", checksum=CHECKSUM)
    assert request.version == "1"
    assert request.checksum == CHECKSUM


@pytest.mark.parametrize(
    ("version", "checksum"),
    [
        ("", CHECKSUM),
        ("version-one", CHECKSUM),
        ("1", ""),
        ("1", "not-a-sha256-digest"),
        ("1", "A" * 64),
    ],
)
def test_bootstrap_request_rejects_invalid_identifiers(version, checksum):
    with pytest.raises(ValueError):
        BootstrapRequest.from_event(
            {
                "BootstrapVersion": version,
                "BootstrapChecksum": checksum,
            }
        )


def test_bootstrap_request_rejects_an_identifier_for_another_package():
    request = BootstrapRequest.from_event(
        {
            "BootstrapVersion": "1",
            "BootstrapChecksum": CHECKSUM,
        }
    )

    with pytest.raises(ValueError, match="deployed package"):
        request.require_expected(version="2", checksum=CHECKSUM)


def test_database_credentials_require_every_rds_secret_field():
    credentials = DatabaseCredentials.from_secret_string(
        json.dumps(
            {
                "username": "flowform_admin",
                "password": "secret",
            }
        ),
        host="database.internal",
        port=5432,
    )

    assert credentials.username == "flowform_admin"
    assert credentials.host == "database.internal"
    assert credentials.port == 5432

    with pytest.raises(ValueError, match="missing required fields"):
        DatabaseCredentials.from_secret_string(
            json.dumps(
                {
                    "username": "flowform_admin",
                }
            ),
            host="database.internal",
            port=5432,
        )


def test_sql_repository_reads_only_the_packaged_bootstrap_assets():
    repository = SqlRepository(
        root=DATABASE_INIT_DIR / "aws",
        schema_root=DATABASE_INIT_DIR / "schema",
    )
    roles_sql = repository.read("roles_v1.sql")
    verification_sql = repository.read("verification_v1.sql")

    assert "CREATE ROLE flowform_owner" in roles_sql
    assert roles_sql.count("LOGIN PASSWORD NULL") == 3
    assert "rolpassword" not in verification_sql
    assert "rds_iam_membership_valid" in verification_sql
    assert "role_privileges_valid" in verification_sql
    assert len(repository.schema_table_names("flowform_core_db_schema_v4.sql")) == 28
    assert repository.schema_table_names("flowform_response_db_schema_v4.sql") == {
        "response_answers",
        "response_envelopes",
    }


def test_schema_load_runs_only_for_an_empty_or_complete_baseline():
    expected_tables = frozenset({"projects", "surveys"})

    assert _requires_schema_load(frozenset(), expected_tables, "flowform_core")
    assert not _requires_schema_load(
        expected_tables,
        expected_tables,
        "flowform_core",
    )

    with pytest.raises(RuntimeError, match="neither empty nor the expected baseline"):
        _requires_schema_load(
            frozenset({"projects"}),
            expected_tables,
            "flowform_core",
        )
