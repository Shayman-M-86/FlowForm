from __future__ import annotations

from datetime import datetime

from app.domain.errors import (
    SubmissionAnswersRequiredError,
    SubmissionInvalidError,
    SubmissionInvalidTimestampsError,
    SubmissionNotFoundError,
)
from app.services.results import LinkedSubmissionResult


def resolve_submission_channel(*, submitted_by_user_id: int | None) -> str:
    return "authenticated" if submitted_by_user_id is not None else "system"


def ensure_user_anonymity_is_valid(
    *,
    submitted_by_user_id: int | None,
    is_anonymous: bool,
) -> None:
    if submitted_by_user_id is None and not is_anonymous:
        raise SubmissionInvalidError("Non-anonymous submissions require a submitting user.")


def ensure_answers_present(*, answers: list[object]) -> None:
    if not answers:
        raise SubmissionAnswersRequiredError()


def ensure_submission_timestamps_are_valid(
    *,
    started_at: datetime | None,
    submitted_at: datetime | None,
) -> None:
    if started_at is not None and submitted_at is not None and submitted_at < started_at:
        raise SubmissionInvalidTimestampsError()

def ensure_submission_exists(
    *,
    linked: LinkedSubmissionResult | None,
    submission_id: int,
) -> LinkedSubmissionResult:
    if linked is None:
        raise SubmissionNotFoundError(submission_id=submission_id)
    return linked


def ensure_submission_belongs_to_project(
    *,
    linked: LinkedSubmissionResult,
    project_id: int,
    submission_id: int,
) -> None:
    if linked.core_submission.project_id != project_id:
        raise SubmissionNotFoundError(submission_id=submission_id)