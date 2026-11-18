from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, model_validator

from app.schema.api.common.base import APIResponseModel
from app.schema.api.responses.surveys import SurveyResponses, SurveyVersionResponses
from app.schema.enums import SurveyLinkAssignmentSource, SurveyLinkType
from app.schema.models.common.types import EmailAddress, Text, Timestamp, Url
from app.schema.models.projects.types import ParticipantId
from app.schema.models.survey.types import SurveyAccessLinkName, SurveyAccessToken, SurveyId, SurveyLinkId


class SurveyAccessLinkResponse(APIResponseModel):
    """API response shape for a survey access link."""

    model_config = ConfigDict(from_attributes=True)

    id: SurveyLinkId
    survey_id: SurveyId
    name: SurveyAccessLinkName
    token: SurveyAccessToken
    is_active: bool
    link_type: SurveyLinkType
    assignment_source: SurveyLinkAssignmentSource
    assigned_participant_id: ParticipantId | None
    assigned_participant_email: EmailAddress | None = None
    expires_at: Timestamp | None
    used_at: Timestamp | None
    emailed_at: Timestamp | None
    created_at: Timestamp

    @model_validator(mode="before")
    @classmethod
    def extract_participant_email(cls, data: Any) -> Any:
        if hasattr(data, "assigned_participant"):
            participant = data.assigned_participant
            if participant is not None and hasattr(participant, "identity"):
                identity = participant.identity
                if identity is not None:
                    data.__dict__["assigned_participant_email"] = identity.normalized_email
        return data


class CreateSurveyAccessLinkResponse(APIResponseModel):
    """API response shape for creating a survey access link."""

    link: SurveyAccessLinkResponse
    url: Url


class ResolveSurveyAccessLinkResponse(APIResponseModel):
    """API response shape for resolving a respondent survey access link token."""

    model_config = ConfigDict(from_attributes=True)
    link: SurveyAccessLinkResponse
    survey: SurveyResponses | None = None
    published_version: SurveyVersionResponses | None = None


class ListSurveyAccessLinksResponse(APIResponseModel):
    """API response shape for listing survey access links for a survey."""

    model_config = ConfigDict(from_attributes=True)
    links: list[SurveyAccessLinkResponse]


class SendSurveyLinkEmailResponse(APIResponseModel):
    """API response shape for sending a survey link email."""

    message_id: Text | None = None
