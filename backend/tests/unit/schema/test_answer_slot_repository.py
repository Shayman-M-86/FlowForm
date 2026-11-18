"""Field-based slot creation and concurrent unique-conflict recovery."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from psycopg.errors import UniqueViolation
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.core import submission_answer_slots
from app.schema.orm.core.submission_answer_slot import ANSWER_SLOT_IDENTITY_CONSTRAINT, SubmissionAnswerSlot


class DuplicateSlot(UniqueViolation):
    @property
    def diag(self):
        return SimpleNamespace(constraint_name=ANSWER_SLOT_IDENTITY_CONSTRAINT)


def inputs():
    return {"submission_session_id": uuid4(), "survey_version_id": 1, "field_uuid": uuid4(), "field_id": "age"}


def test_slot_creation_uses_field_identity():
    db = Mock(spec=Session)
    data = inputs()
    slot = submission_answer_slots.get_or_create(db, **data)
    assert slot.field_uuid == data["field_uuid"] and slot.field_id == "age"
    db.add.assert_called_once_with(slot)
    db.begin_nested.return_value.commit.assert_called_once()
    db.scalar.assert_not_called()


def test_conflicting_creation_returns_existing_field_slot():
    db = Mock(spec=Session)
    data = inputs()
    existing = SubmissionAnswerSlot(**data)
    db.begin_nested.return_value.commit.side_effect = IntegrityError("insert", {}, DuplicateSlot())
    db.scalar.return_value = existing
    assert submission_answer_slots.get_or_create(db, **data) is existing
    db.begin_nested.return_value.rollback.assert_called_once()
    query = db.scalar.call_args.args[0].compile(dialect=postgresql.dialect())
    assert data["field_uuid"] in query.params.values()
    assert data["submission_session_id"] in query.params.values()
    assert "question_node_id" not in str(query)


def test_unrelated_integrity_failure_is_not_swallowed():
    db = Mock(spec=Session)
    error = IntegrityError("insert", {}, ValueError("unrelated failure"))
    db.begin_nested.return_value.commit.side_effect = error
    with pytest.raises(IntegrityError) as caught:
        submission_answer_slots.get_or_create(db, **inputs())
    assert caught.value is error
    db.scalar.assert_not_called()
