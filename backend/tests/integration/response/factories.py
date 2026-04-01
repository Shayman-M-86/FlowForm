from __future__ import annotations

import random

from app.models.response import Submission, SubmissionAnswer, SubmissionEvent


def make_submission(
    core_submission_id: int | None = None,
    survey_id: int = 1,
    survey_version_id: int = 1,
    project_id: int = 1,
    is_anonymous: bool = False,
) -> Submission:
    submission = Submission()
    if core_submission_id is None:
        core_submission_id = random.randint(1, 2**63 - 1)
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
