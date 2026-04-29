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


class UpdateNodeRequest(BaseModel):
    """Validates partial updates to an existing survey content node."""

    model_config = ConfigDict(extra="forbid")

    sort_key: int | None = Field(default=None, gt=0)
    content: QuestionSchemaIn | RuleSchemaIn | None = None
