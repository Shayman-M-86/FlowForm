from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from app.schema.orm.core.survey_submission import SurveySubmission


class AnswerOut(BaseModel):
    """API response shape for a single submission answer."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    question_key: str
    answer_family: str
    answer_value: dict
    created_at: datetime


class SubmitterOut(BaseModel):
    """Lightweight submission submitter identity."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str | None


class CoreSubmissionOut(BaseModel):
    """API response shape for a core submission record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    survey_id: int
    survey_version_id: int
    response_store_id: int
    submission_channel: str
    submitted_by_user_id: int | None
    survey_link_id: int | None
    submitter: SubmitterOut | None = None
    is_anonymous: bool
    status: str
    started_at: datetime | None
    submitted_at: datetime | None
    created_at: datetime

    @classmethod
    def from_submission(cls, submission: "SurveySubmission") -> "CoreSubmissionOut":
        return cls(
            id=submission.id,
            project_id=submission.project_id,
            survey_id=submission.survey_id,
            survey_version_id=submission.survey_version_id,
            response_store_id=submission.response_store_id,
            submission_channel=submission.submission_channel,
            submitted_by_user_id=submission.submitted_by_user_id,
            survey_link_id=submission.survey_link_id,
            submitter=(
                SubmitterOut.model_validate(submission.submitted_by)
                if submission.submitted_by is not None
                else None
            ),
            is_anonymous=submission.is_anonymous,
            status=submission.status,
            started_at=submission.started_at,
            submitted_at=submission.submitted_at,
            created_at=submission.created_at,
        )


class LinkedSubmissionOut(BaseModel):
    """API response shape combining a core submission record with its answers."""

    model_config = ConfigDict(from_attributes=True)

    core: CoreSubmissionOut
    answers: list[AnswerOut]


class PaginatedSubmissionsOut(BaseModel):
    """API response shape for a paginated list of submissions."""
    items: list[CoreSubmissionOut]
    total: int
    page: int
    page_size: int
