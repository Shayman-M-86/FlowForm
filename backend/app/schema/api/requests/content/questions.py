from pydantic import BaseModel, field_validator, model_validator

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

    @model_validator(mode="after")
    def validate_id_matches_question_key(self):
        if self.question_schema.id != self.question_key:
            raise ValueError(
                f"question_schema.id must match question_key "
                f"(id: '{self.question_schema.id}', question_key: '{self.question_key}')"
            )
        return self


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
