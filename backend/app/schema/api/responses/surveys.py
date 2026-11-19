from pydantic import ConfigDict

from app.schema.api.common.base import APIResponseModel
from app.schema.api.common.types import PageItems, ProjectPermissionSet
from app.schema.enums import SurveyVersionStatus, SurveyVisibility
from app.schema.models.survey_document.document import SurveyDefinition
from app.schema.types import (
    Count,
    PageNumber,
    PageSize,
    ProjectId,
    ResponseStoreId,
    Slug,
    SurveyId,
    SurveyTitle,
    SurveyVersionId,
    SurveyVersionNumber,
    Timestamp,
    UserId,
)


class MySurveyPermissionsResponses(APIResponseModel):
    """API response shape for the current user's effective permissions on a survey."""

    permissions: ProjectPermissionSet


class SurveyResponses(APIResponseModel):
    """API response shape for a survey."""

    model_config = ConfigDict(from_attributes=True)

    id: SurveyId
    project_id: ProjectId
    title: SurveyTitle
    visibility: SurveyVisibility
    public_slug: Slug | None
    default_response_store_id: ResponseStoreId | None
    published_version_id: SurveyVersionId | None
    created_by_user_id: UserId | None
    created_at: Timestamp
    updated_at: Timestamp


class SurveyVersionResponses(APIResponseModel):
    """API response shape for a survey version."""

    model_config = ConfigDict(from_attributes=True)

    id: SurveyVersionId
    survey_id: SurveyId
    version_number: SurveyVersionNumber
    status: SurveyVersionStatus
    definition: SurveyDefinition
    published_at: Timestamp | None
    created_by_user_id: UserId | None
    created_at: Timestamp
    updated_at: Timestamp


class PublicSurveyResponses(APIResponseModel):
    """API response shape for a publicly accessible survey with its published version."""

    survey: SurveyResponses
    published_version: SurveyVersionResponses | None = None


class PaginatedPublicSurveysResponses(APIResponseModel):
    """API response shape for a paginated list of public surveys."""

    items: PageItems[SurveyResponses]
    total: Count
    page: PageNumber
    page_size: PageSize
