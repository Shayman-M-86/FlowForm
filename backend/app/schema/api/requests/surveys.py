from typing import Annotated

from pydantic import Field

from app.schema import limits
from app.schema.api.common.base import APIRequestModel
from app.schema.enums import SurveyVisibility
from app.schema.models.common.survey_access import NonPublicSurveyAccess, PublicSurveyAccess
from app.schema.models.survey_document.document import SurveyContent
from app.schema.types import DocumentRevision, PageNumber, PageSize, Slug, SurveyTitle


class PublicSurveyCreateRequest(PublicSurveyAccess, APIRequestModel):
    """Create a public survey with a required public slug."""

    title: SurveyTitle


class NonPublicSurveyCreateRequest(NonPublicSurveyAccess, APIRequestModel):
    """Create a private or link-only survey without a public slug."""

    title: SurveyTitle


CreateSurveyRequest = Annotated[
    PublicSurveyCreateRequest | NonPublicSurveyCreateRequest,
    Field(discriminator="visibility", title="CreateSurveyRequest"),
]


class UpdateSurveyRequest(APIRequestModel):
    """Request body for partially updating a survey."""

    title: SurveyTitle | None = None
    visibility: SurveyVisibility | None = None
    public_slug: Slug | None = None


class CreateVersionRequest(APIRequestModel):
    """Request body for creating a new survey version."""

    pass


class ListPublicSurveysRequest(APIRequestModel):
    """Query parameters for listing public surveys."""

    page: PageNumber = limits.LIST_PAGE_DEFAULT
    page_size: PageSize = limits.LIST_PAGE_SIZE_DEFAULT


class SaveSurveyRequest(APIRequestModel):
    """Replace the content of the draft at the revision the editor read."""

    expected_revision: DocumentRevision
    content: SurveyContent
