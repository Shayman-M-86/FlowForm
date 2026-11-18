from typing import Annotated, Literal

from pydantic import Field

from app.schema import limits
from app.schema.api.common.base import APIRequestModel
from app.schema.api.common.types import PageNumber, PageSize
from app.schema.enums import SurveyVisibility
from app.schema.models.survey.document import SurveyDefinition
from app.schema.types import Slug, SurveyTitle


class PublicSurveyCreateRequest(APIRequestModel):
    """Create a public survey with a required public slug."""

    title: SurveyTitle
    visibility: Literal["public"]
    public_slug: Slug


class NonPublicSurveyCreateRequest(APIRequestModel):
    """Create a private or link-only survey without a public slug."""

    title: SurveyTitle
    visibility: Literal["private", "link_only"]
    public_slug: None = None


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


class SaveSurveyDocumentRequest(APIRequestModel):
    """Replace the survey definition with a complete V2 document."""

    definition: SurveyDefinition
