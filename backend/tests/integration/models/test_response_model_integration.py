from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from app.models.response.submission import Submission
from app.models.response.submission_answer import SubmissionAnswer
from app.models.response.submission_event import SubmissionEvent


def make_submission(
    core_submission_id: int,
    survey_id: int = 1,
    survey_version_id: int = 1,
    project_id: int = 1,
    is_anonymous: bool = False,
) -> Submission:
    submission = Submission()
    submission.core_submission_id = core_submission_id
    submission.survey_id = survey_id
    submission.survey_version_id = survey_version_id
    submission.project_id = project_id
    submission.is_anonymous = is_anonymous
    return submission


def make_submission_answer(
    submission_id: int,
    question_key: str,
    answer_family: str = "field",
    answer_value: dict | None = None,
) -> SubmissionAnswer:
    answer = SubmissionAnswer()
    answer.submission_id = submission_id
    answer.question_key = question_key
    answer.answer_family = answer_family
    answer.answer_value = answer_value or {"value": "hello"}
    return answer


def make_submission_event(
    event_type: str,
    event_payload: dict | None = None,
) -> SubmissionEvent:
    event = SubmissionEvent()
    event.event_type = event_type
    event.event_payload = event_payload
    return event


def test_submission_answer_unique_question_per_submission(db_session: scoped_session[Session]):
    submission = make_submission(core_submission_id=999)
    db_session.add(submission)
    db_session.flush()

    answer_a = make_submission_answer(
        submission_id=submission.id,
        question_key="q1",
        answer_family="field",
        answer_value={"value": "hello"},
    )
    db_session.add(answer_a)
    db_session.flush()

    answer_b = make_submission_answer(
        submission_id=submission.id,
        question_key="q1",
        answer_family="field",
        answer_value={"value": "again"},
    )
    db_session.add(answer_b)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_submission_relationships_work(db_session: scoped_session[Session]):
    submission = make_submission(core_submission_id=100, is_anonymous=True)

    answer = SubmissionAnswer()
    answer.question_key = "age"
    answer.answer_family = "field"
    answer.answer_value = {"value": 24}

    event = make_submission_event(
        event_type="queued",
        event_payload={"destination": "warehouse"},
    )

    submission.answers.append(answer)
    submission.events.append(event)

    db_session.add(submission)
    db_session.flush()
    db_session.refresh(submission)

    assert len(submission.answers) == 1
    assert len(submission.events) == 1
    assert submission.answers[0].submission_id == submission.id
    assert submission.events[0].submission_id == submission.id

