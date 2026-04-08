from pydantic import BaseModel, ConfigDict, field_validator

from app.schema.api.requests.content.rule_schemas import RuleSchemaIn


class CreateRuleRequest(BaseModel):
    """Validates requests that create a new rule schema entry."""
    model_config = ConfigDict(extra="forbid")

    rule_key: str
    rule_schema: RuleSchemaIn

    @field_validator("rule_key")
    @classmethod
    def validate_rule_key(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("rule_key must not be blank")
        return value


class UpdateRuleRequest(BaseModel):
    """Validates requests that partially update a rule schema entry."""
    model_config = ConfigDict(extra="forbid")

    rule_key: str | None = None
    rule_schema: RuleSchemaIn | None = None

    @field_validator("rule_key")
    @classmethod
    def validate_rule_key(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("rule_key must not be blank")
        return value