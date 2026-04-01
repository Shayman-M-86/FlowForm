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

    assert len(submission.events) == 1
    assert submission.events[0].submission_id == submission.id
    assert submission.events[0].event_type == "queued"
