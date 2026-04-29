from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schema.api.requests.content.rule_schemas import RuleSchemaIn


class CreateRuleRequest(BaseModel):
    """Validates requests that create a new rule node in survey_questions."""

    model_config = ConfigDict(extra="forbid")

    rule_key: str
    sort_key: int = Field(gt=0)
    rule_schema: RuleSchemaIn

    @field_validator("rule_key")
    @classmethod
    def validate_rule_key(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("rule_key must not be blank")
        return value

    @model_validator(mode="after")
    def validate_id_matches_rule_key(self) -> CreateRuleRequest:
        if self.rule_schema.id != self.rule_key:
            raise ValueError(
                f"rule_schema.id must match rule_key "
                f"(id: '{self.rule_schema.id}', rule_key: '{self.rule_key}')"
            )
        return self


class UpdateRuleRequest(BaseModel):
    """Validates requests that partially update a rule node."""

    model_config = ConfigDict(extra="forbid")

    rule_key: str | None = None
    sort_key: int | None = Field(default=None, gt=0)
    rule_schema: RuleSchemaIn | None = None

    @field_validator("rule_key")
    @classmethod
    def validate_rule_key(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("rule_key must not be blank")
        return value
