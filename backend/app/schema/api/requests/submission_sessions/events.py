from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.schema.api.content.common import FieldId
from app.schema.enums import SubmissionSessionClientEventType


class SubmissionSessionEventRequest(BaseModel):
    """Request body for recording a respondent session event."""

    model_config = ConfigDict(extra="forbid")

    event_type: SubmissionSessionClientEventType
    field_id: FieldId
