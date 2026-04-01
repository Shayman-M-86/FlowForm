from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, scoped_session

from app.core.extensions import db
from app.db.base import ResponseBase
from app.models.response import Submission, SubmissionAnswer, SubmissionEvent


def assert_model_uses_response_db(
    session: scoped_session[Session],
    model: type[ResponseBase],
) -> None:
    assert issubclass(model, ResponseBase), (
        f"{model.__name__} is not a subclass of ResponseBase"
    )
    assert model.metadata is ResponseBase.metadata, (
        f"{model.__name__}.metadata is not the ResponseBase metadata"
    )

    bind = session.get_bind(mapper=model.__mapper__)
    assert str(bind.engine.url) == str(db.engines["response"].url), (
        f"{model.__name__} bound to {bind.engine.url!r}, expected {db.engines['response'].url!r}"
    )

    response_conn = session.connection(bind_arguments={"mapper": model.__mapper__})
    db_name, schema_name = response_conn.execute(text("select current_database(), current_schema()")).one()

    assert db_name == "flowform_response", (
        f"{model.__name__} resolved to wrong database: db={db_name}, schema={schema_name}, bind={bind.engine.url}"
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
    db_session: scoped_session[Session],
    model: type[ResponseBase],
) -> None:
    assert_model_uses_response_db(db_session, model)
