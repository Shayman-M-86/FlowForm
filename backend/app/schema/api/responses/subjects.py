from typing import Any

from pydantic import ConfigDict, model_validator

from app.schema.api.common.base import APIResponseModel
from app.schema.api.common.types import PageItems, PageNumber, PageSize
from app.schema.enums import SubjectIdentityType, SubjectIdentityVerificationStatus
from app.schema.models.common.types import Count, EmailAddress, Timestamp
from app.schema.models.projects.types import ParticipantId, SubjectCode, SubjectId, SubjectIdentityId


class SubjectIdentityResponse(APIResponseModel):
    """Read-only identity attached to a subject."""

    model_config = ConfigDict(from_attributes=True)

    id: SubjectIdentityId
    identity_type: SubjectIdentityType
    normalized_email: EmailAddress | None
    verification_status: SubjectIdentityVerificationStatus
    attached_at: Timestamp
    revoked_at: Timestamp | None


class SubjectResponse(APIResponseModel):
    """List-item shape for a project subject."""

    model_config = ConfigDict(from_attributes=True)

    id: SubjectId
    subject_code: SubjectCode
    canonical_subject_id: SubjectId | None
    is_participant: bool
    participant_id: ParticipantId | None
    active_identity_count: Count
    created_at: Timestamp

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


class SubjectDetailResponse(APIResponseModel):
    """Detail shape for a single project subject."""

    model_config = ConfigDict(from_attributes=True)

    id: SubjectId
    subject_code: SubjectCode
    canonical_subject_id: SubjectId | None
    is_participant: bool
    participant_id: ParticipantId | None
    identities: list[SubjectIdentityResponse]
    created_at: Timestamp

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


class ListSubjectsResponse(APIResponseModel):
    """Paginated project subject listing."""

    subjects: PageItems[SubjectResponse]
    total: Count
    page: PageNumber
    page_size: PageSize
