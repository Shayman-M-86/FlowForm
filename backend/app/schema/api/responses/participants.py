from typing import Any

from pydantic import ConfigDict, model_validator

from app.schema.api.common.base import APIResponseModel
from app.schema.api.common.types import PageItems, PageNumber, PageSize
from app.schema.types import Count, EmailAddress, ParticipantId, SubjectCode, SubjectId, Timestamp


class ParticipantResponses(APIResponseModel):
    """API response shape for a project participant."""

    model_config = ConfigDict(from_attributes=True)

    id: ParticipantId
    subject_id: SubjectId
    subject_code: SubjectCode
    email: EmailAddress | None
    created_at: Timestamp

    @model_validator(mode="before")
    @classmethod
    def _extract_identity_fields(cls, data: Any) -> Any:
        if isinstance(data, dict) or not hasattr(data, "identity"):
            return data
        return {
            "id": data.id,
            "subject_id": data.project_subject_id,
            "subject_code": data.subject.subject_code,
            "email": data.identity.normalized_email,
            "created_at": data.created_at,
        }


class ListParticipantsResponses(APIResponseModel):
    """API response shape for listing a project's participants."""

    participants: PageItems[ParticipantResponses]
    total: Count
    page: PageNumber
    page_size: PageSize
