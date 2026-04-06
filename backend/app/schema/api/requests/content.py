from pydantic import BaseModel


class CreateQuestionRequest(BaseModel):
    question_key: str
    question_schema: dict


class UpdateQuestionRequest(BaseModel):
    question_key: str | None = None
    question_schema: dict | None = None


class CreateRuleRequest(BaseModel):
    rule_key: str
    rule_schema: dict


class UpdateRuleRequest(BaseModel):
    rule_key: str | None = None
    rule_schema: dict | None = None


class CreateScoringRuleRequest(BaseModel):
    scoring_key: str
    scoring_schema: dict


class UpdateScoringRuleRequest(BaseModel):
    scoring_key: str | None = None
    scoring_schema: dict | None = None
