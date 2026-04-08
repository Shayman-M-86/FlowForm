from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schema.api.responses.surveys import SurveyOut, SurveyVersionOut


class PublicLinkOut(BaseModel):
    """API response shape for a public link."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    survey_id: int
    token_prefix: str
    is_active: bool
    allow_response: bool
    expires_at: datetime | None
    created_at: datetime


class PublicLinkCreatedOut(BaseModel):
    """API response returned once when a public link is created, including the plaintext token."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    survey_id: int
    token: str  # plaintext — returned once only, never stored
    token_prefix: str
    is_active: bool
    allow_response: bool
    expires_at: datetime | None
    created_at: datetime

class CreatePublicLinkOut(BaseModel):
    """API response shape for creating a public link."""
    link: PublicLinkOut
    token: str
    url: str

class ResolveLinkOut(BaseModel):
    """API response shape for resolving a public link token."""

    model_config = ConfigDict(from_attributes=True)
    link: PublicLinkOut
    survey: SurveyOut | None = None
    published_version: SurveyVersionOut | None = None

class ListPublicLinksOut(BaseModel):
    """API response shape for listing all public links for a survey."""

    model_config = ConfigDict(from_attributes=True)
    links: list[PublicLinkOut]