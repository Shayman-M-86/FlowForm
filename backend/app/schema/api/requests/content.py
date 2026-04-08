from pydantic import BaseModel


class CreateQuestionRequest(BaseModel):
    """Request body for creating a new survey question."""

    question_key: str
    question_schema: dict


class UpdateQuestionRequest(BaseModel):
    """Request body for partially updating a survey question."""

    question_key: str | None = None
    question_schema: dict | None = None


class CreateRuleRequest(BaseModel):
    """Request body for creating a new survey rule."""

    rule_key: str
    rule_schema: dict


class UpdateRuleRequest(BaseModel):
    """Request body for partially updating a survey rule."""

    rule_key: str | None = None
    rule_schema: dict | None = None


class CreateScoringRuleRequest(BaseModel):
    """Request body for creating a new scoring rule."""

    scoring_key: str
    scoring_schema: dict


class UpdateScoringRuleRequest(BaseModel):
    """Request body for partially updating a scoring rule."""

    scoring_key: str | None = None
    scoring_schema: dict | None = None
