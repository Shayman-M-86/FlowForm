from pydantic import BaseModel

from app.schema.api.requests.content.questions_schemas import QuestionSchemaIn


class CreateQuestionRequest(BaseModel):
    """Validates requests that create a new question schema entry."""
    question_key: str
    question_schema: QuestionSchemaIn


class UpdateQuestionRequest(BaseModel):
    """Validates requests that update an existing question schema entry."""
    question_key: str | None = None
    question_schema: QuestionSchemaIn | None = None
