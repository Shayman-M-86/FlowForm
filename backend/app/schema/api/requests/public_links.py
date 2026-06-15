from uuid import UUID

from pydantic import BaseModel

from app.schema.api.requests.field_types import (
    FutureExpiresAt,
    PublicLinkName,
    PublicLinkToken,
)
from app.schema.enums import SurveyLinkAssignmentSource, SurveyLinkType


class CreatePublicLinkRequest(BaseModel):
    """Request body for creating a new public link."""
    name: PublicLinkName
    link_type: SurveyLinkType = "general"
    assignment_source: SurveyLinkAssignmentSource = "manual"
    assigned_participant_id: UUID | None = None
    expires_at: FutureExpiresAt | None = None


class UpdatePublicLinkRequest(BaseModel):
    """Request body for updating a public link."""
    is_active: bool | None = None
    name: PublicLinkName | None = None
    link_type: SurveyLinkType | None = None
    assignment_source: SurveyLinkAssignmentSource | None = None
    assigned_participant_id: UUID | None = None
    expires_at: FutureExpiresAt | None = None


class ResolveTokenRequest(BaseModel):
    """Request body for resolving a public link token."""
    token: PublicLinkToken
