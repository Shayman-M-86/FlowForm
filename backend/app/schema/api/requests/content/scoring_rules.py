from pydantic import BaseModel, ConfigDict, field_validator

from app.schema.api.requests.content.scoring_rule_schemas import ScoringRuleSchemaIn


class CreateScoringRuleRequest(BaseModel):
    """Validates requests that create a new scoring rule schema entry."""

    model_config = ConfigDict(extra="forbid")

    scoring_key: str
    scoring_schema: ScoringRuleSchemaIn

    @field_validator("scoring_key")
    @classmethod
    def validate_scoring_key(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("scoring_key must not be blank")
        return value


class UpdateScoringRuleRequest(BaseModel):
    """Validates requests that partially update a scoring rule schema entry."""

    model_config = ConfigDict(extra="forbid")

    scoring_key: str | None = None
    scoring_schema: ScoringRuleSchemaIn | None = None

    @field_validator("scoring_key")
    @classmethod
    def validate_scoring_key(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("scoring_key must not be blank")
        return value