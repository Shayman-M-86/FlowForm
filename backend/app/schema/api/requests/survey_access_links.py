from app.schema.api.common.base import APIRequestModel
from app.schema.api.common.types import FutureExpiry
from app.schema.enums import SurveyLinkAssignmentSource, SurveyLinkType
from app.schema.models.projects.types import ParticipantId
from app.schema.models.survey.types import SurveyAccessLinkName, SurveyAccessToken


class CreateSurveyAccessLinkRequest(APIRequestModel):
    """Request body for creating a new survey access link."""

    name: SurveyAccessLinkName
    link_type: SurveyLinkType = "general"
    assignment_source: SurveyLinkAssignmentSource = "manual"
    assigned_participant_id: ParticipantId | None = None
    expires_at: FutureExpiry | None = None


class UpdateSurveyAccessLinkRequest(APIRequestModel):
    """Request body for updating a survey access link."""

    is_active: bool | None = None
    name: SurveyAccessLinkName | None = None
    link_type: SurveyLinkType | None = None
    assignment_source: SurveyLinkAssignmentSource | None = None
    assigned_participant_id: ParticipantId | None = None
    expires_at: FutureExpiry | None = None


class ResolveSurveyAccessLinkTokenRequest(APIRequestModel):
    """Request body for resolving a respondent survey access link token."""

    token: SurveyAccessToken
