from uuid import UUID

from pydantic import BaseModel

from app.schema.api.common.fields import (
    FutureExpiresAt,
    PublicLinkName,
    PublicLinkToken,
)
from app.schema.enums import SurveyLinkAssignmentSource, SurveyLinkType


class CreateSurveyAccessLinkRequest(BaseModel):
    """Request body for creating a new survey access link."""

    name: PublicLinkName
    link_type: SurveyLinkType = "general"
    assignment_source: SurveyLinkAssignmentSource = "manual"
    assigned_participant_id: UUID | None = None
    expires_at: FutureExpiresAt | None = None


class UpdateSurveyAccessLinkRequest(BaseModel):
    """Request body for updating a survey access link."""

    is_active: bool | None = None
    name: PublicLinkName | None = None
    link_type: SurveyLinkType | None = None
    assignment_source: SurveyLinkAssignmentSource | None = None
    assigned_participant_id: UUID | None = None
    expires_at: FutureExpiresAt | None = None


class ResolveSurveyAccessLinkTokenRequest(BaseModel):
    """Request body for resolving a respondent survey access link token."""

    token: PublicLinkToken
