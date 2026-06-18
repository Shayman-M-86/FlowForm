from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schema.api.submission_sessions.answer_payload import SubmissionAnswerValue
from app.schema.enums import AnswerFamily, SubmissionAnswerState


class SubmissionSessionAnswerResponse(BaseModel):
    """Canonical latest answer state returned to a respondent."""

    question_node_id: UUID
    state: SubmissionAnswerState
    answer_family: AnswerFamily | None = None
    answer_value: SubmissionAnswerValue | None = None
    revision_number: int
    client_mutation_id: UUID
    saved_at: datetime
