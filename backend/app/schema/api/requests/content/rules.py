from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schema.api import limits
from app.schema.api.requests.content.rule_schemas import RuleSchemaIn
from app.schema.api.requests.field_types import SchemaIdStr


class CreateRuleRequest(BaseModel):
    """Validates requests that create a new rule node in survey_questions."""

    model_config = ConfigDict(extra="forbid")

    rule_key: SchemaIdStr
    sort_key: int = Field(gt=limits.CONTENT_SORT_KEY_MIN_EXCLUSIVE)
    rule_schema: RuleSchemaIn

    @model_validator(mode="after")
    def validate_id_matches_rule_key(self) -> CreateRuleRequest:
        if self.rule_schema.id != self.rule_key:
            raise ValueError(
                f"rule_schema.id must match rule_key (id: '{self.rule_schema.id}', rule_key: '{self.rule_key}')"
            )
        return self


class UpdateRuleRequest(BaseModel):
    """Validates requests that partially update a rule node."""

    model_config = ConfigDict(extra="forbid")

    rule_key: SchemaIdStr | None = None
    sort_key: int | None = Field(default=None, gt=limits.CONTENT_SORT_KEY_MIN_EXCLUSIVE)
    rule_schema: RuleSchemaIn | None = None
