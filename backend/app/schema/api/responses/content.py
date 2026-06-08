from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schema.api.requests.content.node import QuestionSchemaIn, RuleSchemaIn


class _NodeResponseBase(BaseModel):
    """Fields shared by question and rule nodes."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: int

    node_key: str = Field(
        validation_alias="question_key",
        serialization_alias="node_key",
    )

    sort_key: int


class QuestionNodeResponse(_NodeResponseBase):
    """API response shape for a question node."""

    node_type: Literal["question"]

    content: QuestionSchemaIn = Field(
        validation_alias="question_schema",
        serialization_alias="content",
    )


class RuleNodeResponse(_NodeResponseBase):
    """API response shape for a rule node."""

    node_type: Literal["rule"]

    content: RuleSchemaIn = Field(
        validation_alias="question_schema",
        serialization_alias="content",
    )


NodeResponses = Annotated[
    QuestionNodeResponse | RuleNodeResponse,
    # An explicit title gives the discriminated union a stable schema name in the
    # OpenAPI export. Without it, the exporter falls back to the type's repr()
    # (typing.Annotated[...]) as the component name, which produces an invalid
    # schema key and breaks the frontend's generated TypeScript.
    Field(discriminator="node_type", title="NodeResponses"),
]


class ScoringRuleResponses(BaseModel):
    """API response shape for a scoring rule."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    survey_version_id: int
    scoring_key: str
    scoring_schema: dict
    created_at: datetime
    updated_at: datetime
