from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


class SubjectIdentityResponse(BaseModel):
    """Read-only identity attached to a subject."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    identity_type: str
    normalized_email: str | None
    verification_status: str
    attached_at: datetime
    revoked_at: datetime | None


class SubjectResponse(BaseModel):
    """List-item shape for a project subject."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    subject_code: str
    canonical_subject_id: UUID | None
    is_participant: bool
    participant_id: UUID | None
    active_identity_count: int
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def _from_row(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data
        subject, identity_count, participant_id = data
        return {
            "id": subject.id,
            "subject_code": subject.subject_code,
            "canonical_subject_id": subject.canonical_subject_id,
            "is_participant": participant_id is not None,
            "participant_id": participant_id,
            "active_identity_count": identity_count,
            "created_at": subject.created_at,
        }


class SubjectDetailResponse(BaseModel):
    """Detail shape for a single project subject."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    subject_code: str
    canonical_subject_id: UUID | None
    is_participant: bool
    participant_id: UUID | None
    identities: list[SubjectIdentityResponse]
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def _from_subject(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data
        subject, participant_id = data
        active_identities = [i for i in subject.identities if i.revoked_at is None]
        return {
            "id": subject.id,
            "subject_code": subject.subject_code,
            "canonical_subject_id": subject.canonical_subject_id,
            "is_participant": participant_id is not None,
            "participant_id": participant_id,
            "identities": active_identities,
            "created_at": subject.created_at,
        }


class ListSubjectsResponse(BaseModel):
    """Paginated project subject listing."""

    subjects: list[SubjectResponse]
    total: int
    page: int
    page_size: int
