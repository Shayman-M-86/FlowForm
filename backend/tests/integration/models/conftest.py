from __future__ import annotations

import logging

import pytest

from app import create_app
from app.core.config import get_settings
from app.core.extensions import db

logger = logging.getLogger("app.tests.integration.models.conftest")


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
            "app": base_settings.app.model_copy(
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
def db_session(app_ctx):
    connection = db.engine.connect()
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
