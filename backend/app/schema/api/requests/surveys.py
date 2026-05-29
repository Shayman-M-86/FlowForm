from pydantic import BaseModel, Field, model_validator

from app.schema.api import limits
from app.schema.api.enums import SurveyVisibility
from app.schema.api.requests.field_types import Slug, SurveyTitle


class CreateSurveyRequest(BaseModel):
    """Request body for creating a new survey."""

    title: SurveyTitle
    visibility: SurveyVisibility = "private"
    public_slug: Slug | None = None

    @model_validator(mode="after")
    def check_visibility_constraints(self) -> CreateSurveyRequest:
        if self.visibility == "public" and not self.public_slug:
            raise ValueError("public_slug is required when visibility is 'public'")
        if self.public_slug and self.visibility != "public":
            raise ValueError("public_slug requires visibility 'public'")
        return self


class UpdateSurveyRequest(BaseModel):
    """Request body for partially updating a survey."""

    title: SurveyTitle | None = None
    visibility: SurveyVisibility | None = None
    public_slug: Slug | None = None


class CreateVersionRequest(BaseModel):
    """Request body for creating a new survey version."""

    pass


class ListPublicSurveysRequest(BaseModel):
    """Query parameters for listing public surveys."""

    page: int = Field(default=limits.LIST_PAGE_DEFAULT, ge=limits.LIST_PAGE_MIN)
    page_size: int = Field(
        default=limits.LIST_PAGE_SIZE_DEFAULT,
        ge=limits.LIST_PAGE_SIZE_MIN,
        le=limits.LIST_PAGE_SIZE_MAX,
    )
