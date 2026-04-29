from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NodeOut(BaseModel):
    """API response shape for a survey content node (question or rule)."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    survey_version_id: int
    node_key: str = Field(validation_alias="question_key")
    sort_key: int
    node_type: str
    content: dict = Field(validation_alias="question_schema")
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
