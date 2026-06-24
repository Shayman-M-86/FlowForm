from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


class ParticipantResponses(BaseModel):
    """API response shape for a project participant."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    subject_id: UUID
    subject_code: str
    email: str | None
    created_at: datetime

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


class ListParticipantsResponses(BaseModel):
    """API response shape for listing a project's participants."""

    participants: list[ParticipantResponses]
    total: int
    page: int
    page_size: int
