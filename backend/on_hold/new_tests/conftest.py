"""Shared fixtures for the proposed backend test suite."""

from __future__ import annotations

import logging
from collections.abc import Generator
from pathlib import Path
from typing import NamedTuple

import pytest
from flask import Flask
from pydantic import SecretStr
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, sessionmaker

from app import create_app
from app.core.config import Settings, get_settings
from app.core.extensions import db_manager
from app.db.base import CoreBase, ResponseBase

logger = logging.getLogger("app.new_tests.conftest")


def pytest_configure() -> None:
    """Configure readable logs for the new backend test suite."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


@pytest.fixture
def secret_key_file(tmp_path: Path) -> Path:
    """Return a mounted-secret-style file containing the Flask secret key."""
    path = tmp_path / "flowform-secret-key"
    path.write_text("test-secret-key\n", encoding="utf-8")
    return path


@pytest.fixture
def core_database_url() -> str:
    """Return a valid core database DSN for settings tests."""
    return "postgresql+psycopg://core_user:core_password@localhost:5432/flowform_core_test"


@pytest.fixture
def response_database_url() -> str:
    """Return a valid response database DSN for settings tests."""
    return "postgresql+psycopg://response_user:response_password@localhost:5432/flowform_response_test"


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Return test settings derived from the normal app settings."""
    base_settings = get_settings()
    app_settings = base_settings.flowform.app.model_copy(
        update={
            "debug": False,
            "secret_key": SecretStr("test-secret"),
        }
    )

    return base_settings.model_copy(
        update={
            "flowform": base_settings.flowform.model_copy(
                update={
                    "env": "test",
                    "app": app_settings,
                }
            ),
        }
    )


@pytest.fixture(scope="session")
def test_settings(settings: Settings) -> Settings:
    """Compatibility alias for config-focused new tests."""
    return settings


@pytest.fixture(scope="session")
def app(settings: Settings) -> Generator[Flask]:
    """Create the Flask app once for the whole test session."""
    flask_app = create_app(settings=settings)
    yield flask_app

    with flask_app.app_context():
        db_manager.dispose()


@pytest.fixture
def app_ctx(app: Flask) -> Generator[Flask]:
    """Push an app context for tests that need Flask context access."""
    with app.app_context():
        yield app


@pytest.fixture
def core_connection(app_ctx: Flask) -> Generator[Connection]:
    """Open a core DB connection wrapped in an outer test transaction."""
    assert app_ctx is not None
    if db_manager.core_engine is None:
        raise RuntimeError("Core engine is not initialized.")

    connection = db_manager.core_engine.connect()
    transaction = connection.begin()

    try:
        yield connection
    finally:
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture
def response_connection(app_ctx: Flask) -> Generator[Connection]:
    """Open a response DB connection wrapped in an outer test transaction."""
    assert app_ctx is not None
    if db_manager.response_engine is None:
        raise RuntimeError("Response engine is not initialized.")

    connection = db_manager.response_engine.connect()
    transaction = connection.begin()

    try:
        yield connection
    finally:
        if transaction.is_active:
            transaction.rollback()
        connection.close()


def _seed_linkage_key_version(session: Session) -> None:
    """Insert a default linkage_key_versions row so FK constraints pass."""
    from app.schema.orm.core.linkage_key_version import LinkageKeyVersion

    existing = session.get(LinkageKeyVersion, 1)
    if existing is None:
        import uuid

        session.add(
            LinkageKeyVersion(
                version=1,
                aws_secret_id="arn:aws:secretsmanager:us-east-1:000:secret:test",
                aws_secret_version_id=uuid.uuid4(),
                is_current=True,
            )
        )
        session.flush()


@pytest.fixture
def core_db_session(core_connection: Connection) -> Generator[Session]:
    """Return a core-only SQLAlchemy session for tests."""
    SessionLocal = sessionmaker(
        bind=core_connection,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
        class_=Session,
    )
    session = SessionLocal()
    _seed_linkage_key_version(session)

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def response_db_session(response_connection: Connection) -> Generator[Session]:
    """Return a response-only SQLAlchemy session for tests."""
    SessionLocal = sessionmaker(
        bind=response_connection,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
        class_=Session,
    )
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def db_session(
    core_connection: Connection,
    response_connection: Connection,
) -> Generator[Session]:
    """Compatibility fixture for older tests.

    This exposes a single Session that can operate on both CoreBase and
    ResponseBase models by binding each base to its own test connection.
    """
    SessionLocal = sessionmaker(
        bind=core_connection,
        binds={
            CoreBase: core_connection,
            ResponseBase: response_connection,
        },
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
        class_=Session,
    )
    session = SessionLocal()
    _seed_linkage_key_version(session)

    try:
        yield session
    finally:
        session.close()


class DbSessions(NamedTuple):
    """Core and response database sessions for cross-database tests."""

    core: Session
    response: Session


@pytest.fixture
def db_sessions(
    core_db_session: Session,
    response_db_session: Session,
) -> Generator[DbSessions]:
    """Return both sessions together for explicit cross-database service tests."""
    yield DbSessions(
        core=core_db_session,
        response=response_db_session,
    )
