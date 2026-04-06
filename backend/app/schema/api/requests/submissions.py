from datetime import datetime

from pydantic import BaseModel


class AnswerIn(BaseModel):
    question_key: str
    answer_family: str
    answer_value: dict


class CreateSubmissionRequest(BaseModel):
    survey_version_id: int
    submitted_by_user_id: int | None = None  # TODO: replace with auth middleware
    is_anonymous: bool = False
    answers: list[AnswerIn] = []
    metadata: dict | None = None
    started_at: datetime | None = None
    submitted_at: datetime | None = None


class PublicSubmissionRequest(BaseModel):
    public_token: str
    survey_version_id: int
    is_anonymous: bool = False
    answers: list[AnswerIn] = []
    metadata: dict | None = None
    started_at: datetime | None = None
    submitted_at: datetime | None = None


class ResolveTokenRequest(BaseModel):
    token: str
