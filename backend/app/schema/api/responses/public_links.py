from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schema.api.responses.surveys import SurveyResponses, SurveyVersionResponses


class PublicLinkResponses(BaseModel):
    """API response shape for a survey link."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    survey_id: int
    name: str
    token_prefix: str
    is_active: bool
    requires_auth: bool
    assigned_email: str | None
    expires_at: datetime | None
    used_at: datetime | None
    created_at: datetime


class PublicLinkCreatedResponses(BaseModel):
    """API response returned once when a survey link is created, including the plaintext token."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    survey_id: int
    name: str
    token: str  # plaintext — returned once only, never stored
    token_prefix: str
    is_active: bool
    requires_auth: bool
    assigned_email: str | None
    expires_at: datetime | None
    used_at: datetime | None
    created_at: datetime


class CreatePublicLinkResponses(BaseModel):
    """API response shape for creating a public link."""

    link: PublicLinkResponses
    token: str
    url: str


class ResolveLinkResponses(BaseModel):
    """API response shape for resolving a public link token."""

    model_config = ConfigDict(from_attributes=True)
    link: PublicLinkResponses
    survey: SurveyResponses | None = None
    published_version: SurveyVersionResponses | None = None


class ListPublicLinksResponses(BaseModel):
    """API response shape for listing all public links for a survey."""

    model_config = ConfigDict(from_attributes=True)
    links: list[PublicLinkResponses]
