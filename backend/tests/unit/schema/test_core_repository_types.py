"""Core repository contracts preserve participant projections and field events."""

from typing import Any, cast
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import TypeAdapter
from sqlalchemy import BigInteger, Integer, MetaData, Table, create_engine, event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.repositories.core import project_subjects, submission_events
from app.schema.orm.core.project import Project
from app.schema.orm.core.project_participant import ProjectParticipant
from app.schema.orm.core.project_subject import ProjectSubject, ProjectSubjectIdentity
from app.schema.orm.core.user import User
from app.schema.types import ProjectId, SubmissionSessionId, SurveyFieldUuid, SurveyVersionId


def test_subject_projection_preserves_participant_identity_and_sql_null():
    metadata = MetaData()
    for model in (User, Project, ProjectSubject, ProjectSubjectIdentity, ProjectParticipant):
        source = model.__table__
        assert isinstance(source, Table)
        table = source.to_metadata(metadata)
        for column in table.columns:
            if isinstance(column.type, BigInteger):
                column.type = column.type.with_variant(Integer(), "sqlite")
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    subject_id, other_subject_id, identity_id, participant_id = (uuid4() for _ in range(4))
    try:
        metadata.create_all(engine)
        with Session(engine) as db:
            db.execute(metadata.tables["projects"].insert().values(id=1, name="Research", slug="research"))
            db.execute(
                metadata.tables["project_subjects"].insert(),
                [
                    {"id": subject_id, "project_id": 1, "subject_code": "enrolled"},
                    {"id": other_subject_id, "project_id": 1, "subject_code": "unenrolled"},
                ],
            )
            db.execute(
                metadata.tables["project_subject_identities"]
                .insert()
                .values(
                    id=identity_id,
                    project_id=1,
                    project_subject_id=subject_id,
                    identity_type="email",
                    normalized_email="person@example.com",
                )
            )
            db.execute(
                metadata.tables["project_participants"]
                .insert()
                .values(id=participant_id, project_id=1, project_subject_id=subject_id, identity_id=identity_id)
            )
            project_id = TypeAdapter(ProjectId).validate_python(1)
            rows, total = project_subjects.list_subjects(db, project_id=project_id)
            assert total == 2
            result = {subject.id: (identity_count, participant) for subject, identity_count, participant in rows}
            assert result == {subject_id: (1, participant_id), other_subject_id: (0, None)}
            for subject, _, expected_participant in rows:
                detail = project_subjects.get_subject_with_participant(db, project_id=project_id, subject_id=subject.id)
                assert detail is not None and detail[1] == expected_participant
    finally:
        engine.dispose()


def event_values():
    return {
        "session_id": TypeAdapter(SubmissionSessionId).validate_python(uuid4()),
        "survey_version_id": TypeAdapter(SurveyVersionId).validate_python(1),
        "event_type": "field_viewed",
        "field_uuid": TypeAdapter(SurveyFieldUuid).validate_python(uuid4()),
    }


def test_event_creation_uses_document_field_identity(monkeypatch):
    db = Mock(spec=Session)
    flush = Mock()
    monkeypatch.setattr(submission_events, "flush_with_err_handle", flush)
    values = event_values()
    row = submission_events.create_event(db, **values)
    assert row.field_uuid == values["field_uuid"]
    assert row.event_metadata == {}
    assert "question_node_id" not in row.__dict__
    db.add.assert_called_once_with(row)
    flush.assert_called_once_with(db, contexts=[row])
    db.commit.assert_not_called()


def test_record_event_preserves_metadata_and_commits(monkeypatch):
    db = Mock(spec=Session)
    monkeypatch.setattr(submission_events, "flush_with_err_handle", Mock())
    metadata = {"source": "respondent", "elapsed_ms": 12}
    submission_events.record_event(db, **event_values(), event_metadata=metadata)
    row = db.add.call_args.args[0]
    assert row.event_metadata == metadata
    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_record_event_keeps_best_effort_failure_behavior(monkeypatch):
    db = Mock(spec=Session)
    monkeypatch.setattr(submission_events, "flush_with_err_handle", Mock(side_effect=SQLAlchemyError("failed")))
    submission_events.record_event(db, **event_values())
    db.commit.assert_not_called()
    db.rollback.assert_called_once()


def test_legacy_node_keyword_is_rejected():
    with pytest.raises(TypeError, match="unexpected keyword"):
        # Deliberately violate the static signature to check Python's rejection.
        cast(Any, submission_events.create_event)(Mock(spec=Session), **event_values(), question_node_id=uuid4())
