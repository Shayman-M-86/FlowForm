from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schema.enums import SubmissionSessionStatus


class StartSubmissionSessionResponse(BaseModel):
    """Session start acknowledgement.

    Survey schema delivery belongs to discovery and link-resolution flows,
    not to session start.
    """

    model_config = ConfigDict(from_attributes=True)

    status: SubmissionSessionStatus
    started_at: datetime
    expires_at: datetime
    survey_version_id: int
    subject_code: str
