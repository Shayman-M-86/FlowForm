from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.permissions import SurveyPermission
from app.schema.api import limits
from app.schema.api.enums import SurveyVersionStatus, SurveyVisibility


class MySurveyPermissionsResponses(BaseModel):
    """API response shape for the current user's effective permissions on a survey."""

    permissions: list[SurveyPermission]


class SurveyResponses(BaseModel):
    """API response shape for a survey."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    visibility: SurveyVisibility
    public_slug: str | None
    default_response_store_id: int | None
    published_version_id: int | None
    created_by_user_id: int | None
    created_at: datetime
    updated_at: datetime


class SurveyVersionResponses(BaseModel):
    """API response shape for a survey version."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    survey_id: int
    version_number: int
    status: SurveyVersionStatus
    compiled_schema: dict | None
    published_at: datetime | None
    created_by_user_id: int | None
    created_at: datetime
    updated_at: datetime


class PublicSurveyResponses(BaseModel):
    """API response shape for a publicly accessible survey with its published version."""

    survey: SurveyResponses
    published_version: SurveyVersionResponses | None = None


class PaginatedPublicSurveysResponses(BaseModel):
    """API response shape for a paginated list of public surveys."""

    items: list[SurveyResponses] = Field(max_length=limits.LIST_PAGE_SIZE_MAX)
    total: int
    page: int
    page_size: int
