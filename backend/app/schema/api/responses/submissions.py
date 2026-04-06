from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_key: str
    answer_family: str
    answer_value: dict
    created_at: datetime


class CoreSubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    survey_id: int
    survey_version_id: int
    response_store_id: int
    submission_channel: str
    submitted_by_user_id: int | None
    public_link_id: int | None
    is_anonymous: bool
    status: str
    started_at: datetime | None
    submitted_at: datetime | None
    created_at: datetime


class LinkedSubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    core: CoreSubmissionOut
    answers: list[AnswerOut]
