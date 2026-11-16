"""Contracts for generating an editable survey builder preview."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schema.api.common.fields import SurveyTitle
from app.schema.api.requests.content.node import CreateQuestionNodeRequest


class AIImportRequest(BaseModel):
    """A short instruction for a survey draft."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    prompt: str = Field(min_length=1, max_length=4000)


class GeneratedQuestion(BaseModel):
    """Small model-facing format, separate from FlowForm node IDs and rules."""

    model_config = ConfigDict(extra="forbid")

    label: str
    type: Literal["text", "single_choice", "multiple_choice", "rating"]
    options: list[str]


class GeneratedSurvey(BaseModel):
    """Structured output expected from OpenAI."""

    model_config = ConfigDict(extra="forbid")

    title: str
    description: str
    questions: list[GeneratedQuestion]


class AIImportResponse(BaseModel):
    """Validated preview; callers can create nodes after reviewing it."""

    title: SurveyTitle
    description: str = Field(max_length=2000)
    nodes: list[CreateQuestionNodeRequest] = Field(min_length=1, max_length=20)
