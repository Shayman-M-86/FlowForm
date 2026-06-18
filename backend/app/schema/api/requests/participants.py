from pydantic import BaseModel

from app.schema.api.common.fields import NormalisedEmail, SubjectCode


class CreateParticipantRequest(BaseModel):
    """Request body for creating a participant (subject + email identity + participant)."""

    email: NormalisedEmail
    subject_code: SubjectCode | None = None


class UpdateParticipantRequest(BaseModel):
    """Request body for updating a participant's assigned email and/or subject code."""

    email: NormalisedEmail | None = None
    subject_code: SubjectCode | None = None
