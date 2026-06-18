from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schema.api import limits
from app.schema.api.requests.helpers import validate_slug


class PublicSlugSessionAccess(BaseModel):
    """Access descriptor for starting a respondent session from a public survey slug."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["public_slug"]
    public_slug: str = Field(max_length=limits.SLUG_MAX)

    @field_validator("public_slug")
    @classmethod
    def validate_public_slug(cls, value: str) -> str:
        return validate_slug(value, field_label="public_slug")


class LinkTokenSessionAccess(BaseModel):
    """Access descriptor for starting a respondent session from a private link token."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["link_token"]
    token: str = Field(max_length=limits.TOKEN_MAX)

    @field_validator("token")
    @classmethod
    def validate_token(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("token must not be blank.")
        return value


SubmissionSessionAccess = Annotated[
    PublicSlugSessionAccess | LinkTokenSessionAccess,
    Field(discriminator="type", title="SubmissionSessionAccess"),
]


class StartSubmissionSessionRequest(BaseModel):
    """Request body for starting or resuming a respondent submission session."""

    model_config = ConfigDict(extra="forbid")

    access: SubmissionSessionAccess
