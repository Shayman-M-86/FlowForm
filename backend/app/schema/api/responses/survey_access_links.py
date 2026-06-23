from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schema.api.responses.surveys import SurveyResponses, SurveyVersionResponses
from app.schema.enums import SurveyLinkAssignmentSource, SurveyLinkType


class SurveyAccessLinkResponse(BaseModel):
    """API response shape for a survey access link."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    survey_id: int
    name: str
    token: str
    is_active: bool
    link_type: SurveyLinkType
    assignment_source: SurveyLinkAssignmentSource
    assigned_participant_id: UUID | None
    expires_at: datetime | None
    used_at: datetime | None
    created_at: datetime


class CreateSurveyAccessLinkResponse(BaseModel):
    """API response shape for creating a survey access link."""

    link: SurveyAccessLinkResponse
    url: str


class ResolveSurveyAccessLinkResponse(BaseModel):
    """API response shape for resolving a respondent survey access link token."""

    model_config = ConfigDict(from_attributes=True)
    link: SurveyAccessLinkResponse
    survey: SurveyResponses | None = None
    published_version: SurveyVersionResponses | None = None


class ListSurveyAccessLinksResponse(BaseModel):
    """API response shape for listing survey access links for a survey."""

    model_config = ConfigDict(from_attributes=True)
    links: list[SurveyAccessLinkResponse]
