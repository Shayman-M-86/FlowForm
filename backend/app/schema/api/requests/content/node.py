from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schema.api.requests.content.questions_schemas import QuestionSchemaIn
from app.schema.api.requests.content.rule_schemas import RuleSchemaIn

NodeType = Literal["question", "rule"]

NodeContentIn = Annotated[
    QuestionSchemaIn | RuleSchemaIn,
    Field(discriminator=None),
]

# Maximum size in bytes of the serialized JSON content for a single node.
# Must stay in sync with the database CHECK constraint
# ``ck_survey_questions_schema_size`` (length(question_schema::text) <= 10000).
# The CHECK remains as defence in depth; this guard fails fast at request time
# so the client gets a clean 422 instead of a DB error.
_MAX_NODE_CONTENT_BYTES = 10_000


def _ensure_content_within_size_budget(content: QuestionSchemaIn | RuleSchemaIn) -> None:
    serialized = content.model_dump_json(by_alias=True)
    size = len(serialized.encode("utf-8"))
    if size > _MAX_NODE_CONTENT_BYTES:
        raise ValueError(
            f"content exceeds the maximum allowed size of {_MAX_NODE_CONTENT_BYTES} bytes (current: {size})"
        )


class CreateNodeRequest(BaseModel):
    """Validates requests that create a new survey content node (question or rule)."""

    model_config = ConfigDict(extra="forbid")

    type: NodeType
    sort_key: int = Field(gt=0)
    content: QuestionSchemaIn | RuleSchemaIn

    @model_validator(mode="after")
    def validate_content_matches_type(self) -> CreateNodeRequest:
        is_question_content = isinstance(self.content, RuleSchemaIn) is False and hasattr(self.content, "family")
        is_rule_content = isinstance(self.content, RuleSchemaIn)
        if self.type == "question" and not is_question_content:
            raise ValueError("content must be a question schema when type is 'question'")
        if self.type == "rule" and not is_rule_content:
            raise ValueError("content must be a rule schema when type is 'rule'")
        return self

    @model_validator(mode="after")
    def validate_content_size(self) -> CreateNodeRequest:
        _ensure_content_within_size_budget(self.content)
        return self


class UpdateNodeRequest(BaseModel):
    """Validates partial updates to an existing survey content node."""

    model_config = ConfigDict(extra="forbid")

    sort_key: int | None = Field(default=None, gt=0)
    content: QuestionSchemaIn | RuleSchemaIn | None = None

    @model_validator(mode="after")
    def validate_content_size(self) -> UpdateNodeRequest:
        if self.content is not None:
            _ensure_content_within_size_budget(self.content)
        return self
