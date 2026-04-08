from datetime import datetime

from pydantic import BaseModel, ConfigDict


class QuestionOut(BaseModel):
    """API response shape for a survey question."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    survey_version_id: int
    question_key: str
    question_schema: dict
    created_at: datetime
    updated_at: datetime


class RuleOut(BaseModel):
    """API response shape for a survey rule."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    survey_version_id: int
    rule_key: str
    rule_schema: dict
    created_at: datetime
    updated_at: datetime


class ScoringRuleOut(BaseModel):
    """API response shape for a scoring rule."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    survey_version_id: int
    scoring_key: str
    scoring_schema: dict
    created_at: datetime
    updated_at: datetime
