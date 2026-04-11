from pydantic import BaseModel, field_validator

from app.schema.api.requests.content.questions_schemas import QuestionSchemaIn


class CreateQuestionRequest(BaseModel):
    """Validates requests that create a new question schema entry."""

    question_key: str
    question_schema: QuestionSchemaIn

    @field_validator("question_key")
    @classmethod
    def validate_question_key(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question_key must not be blank.")
        return value


class UpdateQuestionRequest(BaseModel):
    """Validates requests that update an existing question schema entry."""

    question_key: str | None = None
    question_schema: QuestionSchemaIn | None = None

    @field_validator("question_key")
    @classmethod
    def validate_question_key(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("question_key must not be blank.")
        return value
