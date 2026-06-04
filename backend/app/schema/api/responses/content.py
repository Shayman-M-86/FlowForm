from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schema.api.enums import SurveyNodeType
from app.schema.api.requests.content.node import QuestionSchemaIn, RuleSchemaIn


class NodeResponses(BaseModel):
    """API response shape for a survey content node (question or rule)."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    node_key: str
    sort_key: int
    node_type: SurveyNodeType
    content: QuestionSchemaIn | RuleSchemaIn


class ScoringRuleResponses(BaseModel):
    """API response shape for a scoring rule."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    survey_version_id: int
    scoring_key: str
    scoring_schema: dict
    created_at: datetime
    updated_at: datetime
