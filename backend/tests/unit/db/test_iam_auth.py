"""Unit tests for RDS IAM database authentication wiring."""

from typing import Any

import pytest  # type: ignore[import]
from sqlalchemy import create_engine

from app.core.config import AwsSettings, DatabaseSettings
from app.core.errors import ConfigError
from app.db import iam_auth
from app.db.iam_auth import RDS_CA_BUNDLE_PATH, attach_iam_auth


class _FakeRdsClient:
    """Records token requests and returns a distinct token each call."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def generate_db_auth_token(self, *, DBHostname: str, Port: int, DBUsername: str) -> str:
        self.calls.append({"host": DBHostname, "port": Port, "user": DBUsername})
        return f"token-{len(self.calls)}"


@pytest.fixture
def fake_rds_client(monkeypatch: pytest.MonkeyPatch) -> _FakeRdsClient:
    client = _FakeRdsClient()
    monkeypatch.setattr(
        iam_auth.RdsIamTokenProvider,
        "_build_client",
        staticmethod(lambda _aws: client),
    )
    return client


def _iam_database() -> DatabaseSettings:
    return DatabaseSettings(
        auth_mode="iam",
        app_user="flowform_core_app",
        host="core.rds.example.test",
        port=5432,
        name="flowform_core",
    )


def _fire_do_connect(engine: Any, cparams: dict[str, Any] | None = None) -> dict[str, Any]:
    """Invoke the registered do_connect handlers and return the params.

    ``do_connect`` is a DialectEvents event, so it dispatches on the engine's
    dialect rather than on the engine itself.
    """
    params: dict[str, Any] = {} if cparams is None else cparams
    for fn in engine.dialect.dispatch.do_connect:
        fn(engine.dialect, None, (), params)
    return params


def test_iam_token_is_injected_as_connection_password(fake_rds_client: _FakeRdsClient) -> None:
    """The do_connect hook supplies a generated token as the password."""
    database = _iam_database()
    engine = create_engine(database.url)

    attach_iam_auth(engine, database=database, aws=AwsSettings())
    cparams = _fire_do_connect(engine)

    assert cparams["password"] == "token-1"
    assert fake_rds_client.calls == [{"host": "core.rds.example.test", "port": 5432, "user": "flowform_core_app"}]


def test_each_connection_gets_a_fresh_token(fake_rds_client: _FakeRdsClient) -> None:
    """Tokens expire, so a new one must be minted per physical connection."""
    database = _iam_database()
    engine = create_engine(database.url)
    attach_iam_auth(engine, database=database, aws=AwsSettings())

    first = _fire_do_connect(engine)
    second = _fire_do_connect(engine)

    assert first["password"] == "token-1"
    assert second["password"] == "token-2"
    assert len(fake_rds_client.calls) == 2


def test_iam_connections_require_tls(fake_rds_client: _FakeRdsClient) -> None:
    """RDS IAM uses hostname verification against the pinned AWS CA bundle."""
    database = _iam_database()
    engine = create_engine(database.url)
    attach_iam_auth(engine, database=database, aws=AwsSettings())

    cparams = _fire_do_connect(engine)

    assert cparams["sslmode"] == "verify-full"
    assert cparams["sslrootcert"] == RDS_CA_BUNDLE_PATH


def test_explicit_sslmode_is_preserved(fake_rds_client: _FakeRdsClient) -> None:
    """An sslmode already chosen by the caller is not overridden."""
    database = _iam_database()
    engine = create_engine(database.url)
    attach_iam_auth(engine, database=database, aws=AwsSettings())

    cparams = _fire_do_connect(engine, {"sslmode": "require"})

    assert cparams["sslmode"] == "require"


def test_explicit_sslrootcert_is_preserved(fake_rds_client: _FakeRdsClient) -> None:
    """A caller-provided trust bundle is not replaced."""
    database = _iam_database()
    engine = create_engine(database.url)
    attach_iam_auth(engine, database=database, aws=AwsSettings())

    cparams = _fire_do_connect(engine, {"sslrootcert": "/custom/rds-ca.pem"})

    assert cparams["sslrootcert"] == "/custom/rds-ca.pem"


def test_attach_requires_host_and_user(fake_rds_client: _FakeRdsClient) -> None:
    """Tokens cannot be signed without a host and user to sign for."""
    database = _iam_database()
    engine = create_engine(database.url)
    database.host = None

    with pytest.raises(ConfigError, match="host and app_user are required"):
        attach_iam_auth(engine, database=database, aws=AwsSettings())
