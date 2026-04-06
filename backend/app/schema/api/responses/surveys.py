from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SurveyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    visibility: str
    allow_public_responses: bool
    public_slug: str | None
    default_response_store_id: int | None
    published_version_id: int | None
    created_by_user_id: int | None
    created_at: datetime
    updated_at: datetime


class SurveyVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    survey_id: int
    version_number: int
    status: str
    compiled_schema: dict | None
    published_at: datetime | None
    created_by_user_id: int | None
    created_at: datetime
    updated_at: datetime
