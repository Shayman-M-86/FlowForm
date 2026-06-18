from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schema.enums import SubmissionSessionClientEventType


class SubmissionSessionEventRequest(BaseModel):
    """Request body for recording a respondent session event."""

    model_config = ConfigDict(extra="forbid")

    event_type: SubmissionSessionClientEventType
    question_node_id: UUID
