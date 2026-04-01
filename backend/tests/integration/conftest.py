from __future__ import annotations

import logging
from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from app import create_app
from app.core.config import get_settings
from app.core.extensions import db
from app.db import init_models as init_models
from app.db.base import CoreBase, ResponseBase

logger = logging.getLogger("app.tests.integration.conftest")


def pytest_configure() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


@pytest.fixture(scope="session")
def settings():
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
    app = create_app(settings=settings)
    yield app

    with app.app_context():
        db.session.remove()

        for engine in db.engines.values():
            engine.dispose()


@pytest.fixture()
def app_ctx(app):
    with app.app_context():
        yield app


@pytest.fixture()
def db_session(app_ctx) -> Generator[scoped_session[Session]]:
    core_connection = db.engine.connect()
    response_connection = db.engines["response"].connect()

    core_transaction = core_connection.begin()
    response_transaction = response_connection.begin()

    SessionFactory = scoped_session(
        sessionmaker(
            bind=core_connection,  # fallback/default
            binds={
                CoreBase: core_connection,
                ResponseBase: response_connection,
            },
            join_transaction_mode="create_savepoint",
        )
    )

    original_session = db.session
    db.session = SessionFactory # type: ignore[assignment]

    try:
        yield SessionFactory
    finally:
        SessionFactory.remove()
        db.session = original_session

        if core_transaction.is_active:
            core_transaction.rollback()
        if response_transaction.is_active:
            response_transaction.rollback()

        core_connection.close()
        response_connection.close()


@pytest.fixture()
def response_db_session(app_ctx):
    connection = db.engines["response"].connect()
    transaction = connection.begin()

    original_session = db.session
    test_session = db._make_scoped_session(
        {
            "bind": connection,
            "join_transaction_mode": "create_savepoint",
        }
    )
    db.session = test_session

    try:
        yield test_session
    finally:
        test_session.remove()
        db.session = original_session
        if transaction.is_active:
            transaction.rollback()
        connection.close()
