from pydantic import ConfigDict, Field

from app.schema.api.common.base import APIResponseModel
from app.schema.api.common.types import PageItems, ProjectPermissionSet
from app.schema.enums import SurveyVersionStatus, SurveyVisibility
from app.schema.models.survey_document.document import SurveyContent
from app.schema.types import (
    Count,
    DocumentRevision,
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


class SurveyVersionListItemResponse(APIResponseModel):
    """Version metadata used to select a version in Studio."""

    version_id: SurveyVersionId
    version_number: SurveyVersionNumber
    revision: DocumentRevision
    status: SurveyVersionStatus
    published_at: Timestamp | None
    created_at: Timestamp
    updated_at: Timestamp


class GetSurveyVersionResponse(APIResponseModel):
    """One version's current metadata and its saved content."""

    version_id: SurveyVersionId
    revision: DocumentRevision
    status: SurveyVersionStatus
    content: SurveyContent | None


class CreateSurveyVersionResponse(APIResponseModel):
    """Identify the newly created empty draft."""

    version_id: SurveyVersionId
    version_number: SurveyVersionNumber
    revision: DocumentRevision


class CopySurveyVersionResponse(APIResponseModel):
    """Identify the new draft that holds the copied content."""

    version_id: SurveyVersionId
    version_number: SurveyVersionNumber
    revision: DocumentRevision


class SaveSurveyResponse(APIResponseModel):
    """Acknowledge the newly saved revision."""

    revision: DocumentRevision


class PublishSurveyResponse(APIResponseModel):
    """Identify the version that was published."""

    version_id: SurveyVersionId
    status: SurveyVersionStatus


class ArchiveSurveyResponse(APIResponseModel):
    """Identify the version that was archived."""

    version_id: SurveyVersionId
    status: SurveyVersionStatus


class RespondentSurveyVersionNestedModel(APIResponseModel):
    """The version identity and content needed to display a survey."""

    version_id: SurveyVersionId = Field(validation_alias="id")
    content: SurveyContent


class PublicSurveyResponses(APIResponseModel):
    """API response shape for a publicly accessible survey with its published version."""

    survey: SurveyResponses
    published_version: RespondentSurveyVersionNestedModel | None = None


class PaginatedPublicSurveysResponses(APIResponseModel):
    """API response shape for a paginated list of public surveys."""

    items: PageItems[SurveyResponses]
    total: Count
    page: PageNumber
    page_size: PageSize
