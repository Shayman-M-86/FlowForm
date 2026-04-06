from datetime import datetime

from pydantic import BaseModel, ConfigDict


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    survey_version_id: int
    question_key: str
    question_schema: dict
    created_at: datetime
    updated_at: datetime


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    survey_version_id: int
    rule_key: str
    rule_schema: dict
    created_at: datetime
    updated_at: datetime


class ScoringRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    survey_version_id: int
    scoring_key: str
    scoring_schema: dict
    created_at: datetime
    updated_at: datetime
