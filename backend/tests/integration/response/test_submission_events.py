from __future__ import annotations

from typing import cast

import pytest
from psycopg.errors import CheckViolation, NotNullViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from app.models.response.submission_event import SubmissionEvent
from tests.integration.response.factories import make_submission, make_submission_event


def test_submission_event_can_be_created(db_session: scoped_session[Session]) -> None:
    """All fields are persisted and the server default populates created_at."""
    submission = make_submission()
    db_session.add(submission)
    db_session.flush()

    event = make_submission_event(event_type="queued", event_payload={"destination": "warehouse"})
    event.submission_id = submission.id
    db_session.add(event)
    db_session.flush()

    saved = db_session.get(SubmissionEvent, event.id)
    assert saved is not None, "SubmissionEvent was not persisted"
    assert saved.submission_id == submission.id, f"submission_id={saved.submission_id!r}, expected {submission.id!r}"
    assert saved.event_type == "queued", f"event_type={saved.event_type!r}, expected 'queued'"
    assert saved.event_payload == {"destination": "warehouse"}, f"event_payload={saved.event_payload!r}"
    assert saved.created_at is not None, "created_at was not set by the server default"


def test_submission_event_payload_is_optional(db_session: scoped_session[Session]) -> None:
    """event_payload is nullable — an event can be created without one."""
    submission = make_submission()
    db_session.add(submission)
    db_session.flush()

    # Do not assign event_payload to avoid psycopg3 sending Jsonb(None) for the JSONB column
    event = SubmissionEvent()
    event.submission_id = submission.id
    event.event_type = "delivered"
    db_session.add(event)
    db_session.flush()

    saved = db_session.get(SubmissionEvent, event.id)
    assert saved is not None, "SubmissionEvent was not persisted"
    assert saved.event_payload is None, f"event_payload={saved.event_payload!r}, expected None"


def test_submission_event_requires_event_type(db_session: scoped_session[Session]) -> None:
    """event_type is NOT NULL — omitting it raises an IntegrityError."""
    submission = make_submission()
    db_session.add(submission)
    db_session.flush()

    event = make_submission_event(event_type="queued")
    event.submission_id = submission.id
    event.event_type = None  # type: ignore[assignment]
    db_session.add(event)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "event_type", (
        f"Expected NOT NULL violation on 'event_type', got '{column}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_submission_event_rejects_non_object_payload(db_session: scoped_session[Session]) -> None:
    """event_payload must be a JSON object when set — arrays and scalars are rejected."""
    submission = make_submission()
    db_session.add(submission)
    db_session.flush()

    event = make_submission_event(event_type="queued", event_payload=["not", "an", "object"])  # type: ignore[arg-type]
    event.submission_id = submission.id
    db_session.add(event)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_submission_events_event_payload_is_object", (
        f"Expected constraint 'ck_submission_events_event_payload_is_object', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_submission_event_accessible_via_relationship(db_session: scoped_session[Session]) -> None:
    """Events added via the ORM relationship are correctly linked to the submission."""
    submission = make_submission()

    event = SubmissionEvent()
    event.event_type = "queued"
    event.event_payload = {"destination": "warehouse"}

    submission.events.append(event)
    db_session.add(submission)
    db_session.flush()
    db_session.refresh(submission)

    assert len(submission.events) == 1, f"Expected 1 event on submission, got {len(submission.events)}"
    assert submission.events[0].submission_id == submission.id, (
        f"event.submission_id={submission.events[0].submission_id!r}, expected {submission.id!r}"
    )
    assert submission.events[0].event_type == "queued", (
        f"event.event_type={submission.events[0].event_type!r}, expected 'queued'"
    )
