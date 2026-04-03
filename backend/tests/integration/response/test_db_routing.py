from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

from app.core.extensions import db_manager
from app.db.base import ResponseBase
from app.schema.orm.response import Submission, SubmissionAnswer, SubmissionEvent


def assert_model_uses_response_db(
    session: Session,
    model: type[ResponseBase],
) -> None:
    assert issubclass(model, ResponseBase), f"{model.__name__} is not a subclass of ResponseBase"
    assert model.metadata is ResponseBase.metadata, f"{model.__name__}.metadata is not the ResponseBase metadata"

    if db_manager.response_engine is None:
        raise RuntimeError("Response engine is not initialized.")

    bind = session.get_bind(mapper=model.__mapper__)
    assert bind is not None, f"No bind resolved for {model.__name__}"

    bind_engine: Engine
    if isinstance(bind, Engine):
        bind_engine = bind
    elif isinstance(bind, Connection):
        bind_engine = bind.engine
    else:
        raise TypeError(f"Unexpected bind type for {model.__name__}: {type(bind).__name__}")

    assert str(bind_engine.url) == str(db_manager.response_engine.url), (
        f"{model.__name__} bound to {bind_engine.url!r}, expected {db_manager.response_engine.url!r}"
    )

    response_conn = session.connection(bind_arguments={"mapper": model.__mapper__})
    db_name, schema_name = response_conn.execute(text("select current_database(), current_schema()")).one()

    assert db_name == "flowform_response", (
        f"{model.__name__} resolved to wrong database: db={db_name}, schema={schema_name}, bind={bind_engine.url}"
    )


@pytest.mark.parametrize(
    "model",
    [
        Submission,
        SubmissionAnswer,
        SubmissionEvent,
    ],
)
def test_response_models_use_response_db(
    db_session: Session,
    model: type[ResponseBase],
) -> None:
    assert_model_uses_response_db(db_session, model)
