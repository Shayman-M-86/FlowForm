from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schema.api.requests.helpers import validate_slug


def _validate_title(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Title must not be blank.")
    if len(value) > 200:
        raise ValueError("Title must be 200 characters or fewer.")
    return value


class CreateSurveyRequest(BaseModel):
    """Request body for creating a new survey."""

    title: str
    visibility: Literal["private", "link_only", "public"] = "private"
    public_slug: str | None = None
    default_response_store_id: int | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _validate_title(value)

    @field_validator("public_slug")
    @classmethod
    def validate_public_slug(cls, value: str | None) -> str | None:
        return validate_slug(value, field_label="Public slug") if value is not None else None

    @model_validator(mode="after")
    def check_visibility_constraints(self) -> CreateSurveyRequest:
        if self.visibility == "public" and not self.public_slug:
            raise ValueError("public_slug is required when visibility is 'public'")
        if self.public_slug and self.visibility != "public":
            raise ValueError("public_slug requires visibility 'public'")
        return self


class UpdateSurveyRequest(BaseModel):
    """Request body for partially updating a survey."""

    title: str | None = None
    visibility: Literal["private", "link_only", "public"] | None = None
    public_slug: str | None = None
    default_response_store_id: int | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        return _validate_title(value) if value is not None else None

    @field_validator("public_slug")
    @classmethod
    def validate_public_slug(cls, value: str | None) -> str | None:
        return validate_slug(value, field_label="Public slug") if value is not None else None


class CreateVersionRequest(BaseModel):
    """Request body for creating a new survey version."""

    pass


class ListPublicSurveysRequest(BaseModel):
    """Query parameters for listing public surveys."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
