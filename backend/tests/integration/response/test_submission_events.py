from __future__ import annotations

from sqlalchemy.orm import Session, scoped_session

from app.models.response.submission_event import SubmissionEvent
from tests.integration.response.factories import make_submission


def test_submission_relationships_events_work(db_session: scoped_session[Session]) -> None:
    submission = make_submission()

    event = SubmissionEvent()
    event.event_type = "queued"
    event.event_payload = {"destination": "warehouse"}

    submission.events.append(event)

    db_session.add(submission)
    db_session.flush()
    db_session.refresh(submission)

    assert len(submission.events) == 1, (
        f"Expected 1 event on submission, got {len(submission.events)}"
    )
    assert submission.events[0].submission_id == submission.id, (
        f"event.submission_id={submission.events[0].submission_id!r}, expected {submission.id!r}"
    )
    assert submission.events[0].event_type == "queued", (
        f"event.event_type={submission.events[0].event_type!r}, expected 'queued'"
    )
