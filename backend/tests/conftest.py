from __future__ import annotations

import logging
from collections.abc import Generator
from typing import NamedTuple

import pytest  # type: ignore[import]
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, sessionmaker

from app import create_app
from app.core.config import get_settings
from app.core.extensions import db_manager
from app.db.base import CoreBase, ResponseBase
from app.logging.logging_config import configure_third_party_loggers
from app.logging.sensitive_data import protect_root_handlers

logger = logging.getLogger("app.tests.integration.conftest")


def pytest_configure() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    configure_third_party_loggers()
    protect_root_handlers()

    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


@pytest.hookimpl(trylast=True)
def pytest_runtest_setup() -> None:
    """Protect capture handlers that pytest installs after initial configuration."""
    protect_root_handlers()


@pytest.fixture(scope="session")
def settings():
    """Return test settings derived from the normal app settings."""
    base_settings = get_settings()

    return base_settings.model_copy(
        update={
            "env": "test",
            "flowform": base_settings.flowform.model_copy(
                update={
                    "debug": False,
                    "secret_key": "test-secret",
                }
            ),
        }
    )


@pytest.fixture(scope="session")
def app(settings):
    """Create the Flask app once for the whole test session."""
    app = create_app(settings=settings)
    yield app

    with app.app_context():
        db_manager.dispose()


@pytest.fixture()
def app_ctx(app):
    """Push an app context for tests that need Flask context access."""
    with app.app_context():
        yield app


@pytest.fixture()
def core_connection(app_ctx) -> Generator[Connection]:
    """Open a core DB connection wrapped in an outer test transaction."""
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


@pytest.fixture()
def response_connection(app_ctx) -> Generator[Connection]:
    """Open a response DB connection wrapped in an outer test transaction."""
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

        session.add(LinkageKeyVersion(
            version=1,
            aws_secret_id="arn:aws:secretsmanager:us-east-1:000:secret:test",
            aws_secret_version_id=uuid.uuid4(),
            is_current=True,
        ))
        session.flush()


@pytest.fixture()
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


@pytest.fixture()
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


@pytest.fixture()
def db_session(
    core_connection: Connection,
    response_connection: Connection,
) -> Generator[Session]:
    """
    Compatibility fixture for older tests.

    This exposes a single Session that can operate on both CoreBase and
    ResponseBase models by binding each base to its own test connection.
    """
    SessionLocal = sessionmaker(
        bind=core_connection,  # default / fallback bind
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
    core: Session
    response: Session


@pytest.fixture()
def db_sessions(
    core_db_session: Session,
    response_db_session: Session,
) -> Generator[DbSessions]:
    """Return both sessions together for explicit cross-database service tests."""
    yield DbSessions(
        core=core_db_session,
        response=response_db_session,
    )
