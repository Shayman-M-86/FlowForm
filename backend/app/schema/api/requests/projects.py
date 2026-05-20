from pydantic import BaseModel, Field, field_validator

from app.schema.api import limits
from app.schema.api.requests.helpers import validate_slug


def _validate_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Name must not be blank.")
    return value


class CreateProjectRequest(BaseModel):
    """Request body for creating a new project."""

    name: str = Field(max_length=limits.PROJECT_NAME_MAX)
    slug: str = Field(max_length=limits.SLUG_MAX)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _validate_name(value)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        return validate_slug(value, field_label="URL-safe name")


class UpdateProjectRequest(BaseModel):
    """Request body for partially updating a project."""

    name: str | None = Field(default=None, max_length=limits.PROJECT_NAME_MAX)
    slug: str | None = Field(default=None, max_length=limits.SLUG_MAX)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        return _validate_name(value) if value is not None else None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str | None) -> str | None:
        return validate_slug(value, field_label="URL-safe name") if value is not None else None
