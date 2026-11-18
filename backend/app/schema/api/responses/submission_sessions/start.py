from __future__ import annotations

from pydantic import ConfigDict

from app.schema.api.common.base import APIResponseModel
from app.schema.api.responses.surveys import SurveyResponses, SurveyVersionResponses
from app.schema.enums import SubmissionSessionStatus
from app.schema.types import SubjectCode, SurveyVersionId, Timestamp


class StartSubmissionSessionResponse(APIResponseModel):
    """Session start acknowledgement.

    Survey schema delivery belongs to discovery and link-resolution flows,
    not to session start.
    """

    model_config = ConfigDict(from_attributes=True)

    status: SubmissionSessionStatus
    started_at: Timestamp
    expires_at: Timestamp
    survey_version_id: SurveyVersionId
    subject_code: SubjectCode


class ResumeSubmissionSessionResponse(APIResponseModel):
    """Published survey context for the matching in-progress browser session."""

    status: SubmissionSessionStatus
    survey: SurveyResponses
    published_version: SurveyVersionResponses
