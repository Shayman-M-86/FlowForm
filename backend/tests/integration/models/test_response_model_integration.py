from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.extensions import db
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
    answer_family: str = "text",
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


def test_submission_answer_unique_question_per_submission(app):
    submission = make_submission(core_submission_id=999)
    db.session.add(submission)
    db.session.commit()

    answer_a = make_submission_answer(
        submission_id=submission.id,
        question_key="q1",
        answer_value={"value": "hello"},
    )
    db.session.add(answer_a)
    db.session.commit()

    answer_b = make_submission_answer(
        submission_id=submission.id,
        question_key="q1",
        answer_value={"value": "again"},
    )
    db.session.add(answer_b)

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_submission_relationships_work(app):
    submission = make_submission(core_submission_id=100, is_anonymous=True)

    answer = SubmissionAnswer()
    answer.question_key = "age"
    answer.answer_family = "number"
    answer.answer_value = {"value": 24}

    event = make_submission_event(
        event_type="queued",
        event_payload={"destination": "warehouse"},
    )

    submission.answers.append(answer)
    submission.events.append(event)

    db.session.add(submission)
    db.session.commit()
    db.session.refresh(submission)

    assert len(submission.answers) == 1
    assert len(submission.events) == 1
    assert submission.answers[0].submission_id == submission.id
    assert submission.events[0].submission_id == submission.id


def test_submission_delete_cascades_answers_and_events(app):
    submission = make_submission(core_submission_id=101, is_anonymous=True)

    answer = SubmissionAnswer()
    answer.question_key = "q1"
    answer.answer_family = "text"
    answer.answer_value = {"value": "x"}

    event = make_submission_event(
        event_type="created",
        event_payload={"ok": True},
    )

    submission.answers.append(answer)
    submission.events.append(event)

    db.session.add(submission)
    db.session.commit()

    submission_id = submission.id
    answer_id = answer.id
    event_id = event.id

    db.session.delete(submission)
    db.session.commit()

    assert db.session.get(Submission, submission_id) is None
    assert db.session.get(SubmissionAnswer, answer_id) is None
    assert db.session.get(SubmissionEvent, event_id) is None
