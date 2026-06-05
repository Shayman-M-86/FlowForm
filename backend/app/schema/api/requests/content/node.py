from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.schema.api import limits
from app.schema.api.requests.content.questions_schemas import QuestionSchemaIn
from app.schema.api.requests.content.rule_schemas import RuleSchemaIn
from app.schema.api.requests.field_types import SchemaIdStr

_MAX_NODE_CONTENT_BYTES = limits.NODE_CONTENT_BYTES_MAX

NodeSortKey = Annotated[int, Field(gt=limits.CONTENT_SORT_KEY_MIN_EXCLUSIVE)]


def _check_content_size(content: QuestionSchemaIn | RuleSchemaIn) -> QuestionSchemaIn | RuleSchemaIn:
    # Must stay in sync with DB CHECK constraint ck_survey_questions_schema_size
    # (length(question_schema::text) <= 10000). This guard gives a clean 422
    # instead of a DB error.
    serialized = content.model_dump_json(by_alias=True)
    size = len(serialized.encode("utf-8"))
    if size > _MAX_NODE_CONTENT_BYTES:
        raise ValueError(
            f"content exceeds the maximum allowed size of {_MAX_NODE_CONTENT_BYTES} bytes (current: {size})"
        )
    return content


SizedQuestionContent = Annotated[QuestionSchemaIn, AfterValidator(_check_content_size)]
SizedRuleContent = Annotated[RuleSchemaIn, AfterValidator(_check_content_size)]


class CreateQuestionNodeRequest(BaseModel):
    """Validates requests that create a new question node."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"x-flowform-export": "builder"})
    
    id: int = Field(gt=0, lt=limits.INT_ID_MAX)
    node_key: SchemaIdStr
    node_type: Literal["question"]
    sort_key: NodeSortKey
    content: SizedQuestionContent


class CreateRuleNodeRequest(BaseModel):
    """Validates requests that create a new rule node."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"x-flowform-export": "builder"})
    
    id: int = Field(gt=0, lt=limits.INT_ID_MAX)
    node_key: SchemaIdStr
    node_type: Literal["rule"]
    sort_key: NodeSortKey
    content: SizedRuleContent


CreateNodeRequest = Annotated[
    CreateQuestionNodeRequest | CreateRuleNodeRequest,
    Field(discriminator="node_type", title="CreateNodeRequest"),
]


class UpdateNodeRequest(BaseModel):
    """Validates partial updates to an existing survey content node."""

    model_config = ConfigDict(extra="forbid")

    id: int = Field(gt=0, lt=limits.INT_ID_MAX)
    node_key: SchemaIdStr | None = None
    node_type: Literal["question", "rule"] | None = None
    sort_key: int | None = Field(default=None, gt=limits.CONTENT_SORT_KEY_MIN_EXCLUSIVE)
    content: Annotated[QuestionSchemaIn | RuleSchemaIn, AfterValidator(_check_content_size)] | None = None
