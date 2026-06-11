from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schema.api import limits
from app.schema.api.requests.helpers import validate_slug
from app.schema.enums import AnswerFamily, SubmissionAnswerState


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


class SaveSubmissionSessionAnswerRequest(BaseModel):
    """Request body for saving or clearing one respondent answer revision."""

    model_config = ConfigDict(extra="forbid")

    client_mutation_id: UUID
    state: SubmissionAnswerState
    answer_family: AnswerFamily | None = None
    answer_value: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_answer_state(self) -> SaveSubmissionSessionAnswerRequest:
        if self.state == "answered":
            if self.answer_family is None:
                raise ValueError("answer_family is required when state is 'answered'.")
            if self.answer_value is None:
                raise ValueError("answer_value is required when state is 'answered'.")
            return self

        if self.answer_family is not None:
            raise ValueError("answer_family must be omitted when state is 'cleared'.")
        if self.answer_value is not None:
            raise ValueError("answer_value must be omitted when state is 'cleared'.")
        return self


class QuestionViewedEventRequest(BaseModel):
    """Request body for recording that a respondent viewed a question."""

    model_config = ConfigDict(extra="forbid")

    question_node_id: UUID
