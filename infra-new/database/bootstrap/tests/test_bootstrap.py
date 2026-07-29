# TODO(migration): Update paths, contracts, and runtime wiring for infra-new before this file is used.
import json
from pathlib import Path

import pytest

from flowform_infra.database_bootstrap.bootstrap.models import (
    BootstrapRequest,
    DatabaseCredentials,
)
from flowform_infra.database_bootstrap.bootstrap.postgres import (
    _requires_schema_load,
)
from flowform_infra.database_bootstrap.bootstrap.services import SqlRepository

CHECKSUM = "a" * 64
DATABASE_INIT_DIR = Path(__file__).parents[5] / "infra" / "database" / "init"


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
