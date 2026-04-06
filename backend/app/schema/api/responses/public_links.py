from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schema.api.responses.surveys import SurveyOut, SurveyVersionOut


class PublicLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    survey_id: int
    token_prefix: str
    is_active: bool
    allow_response: bool
    expires_at: datetime | None
    created_at: datetime


class PublicLinkCreatedOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    survey_id: int
    token: str  # plaintext — returned once only, never stored
    token_prefix: str
    is_active: bool
    allow_response: bool
    expires_at: datetime | None
    created_at: datetime


class ResolveLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    link: PublicLinkOut
    survey: SurveyOut | None = None
    published_version: SurveyVersionOut | None = None
