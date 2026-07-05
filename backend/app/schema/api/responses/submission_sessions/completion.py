from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class CompleteSubmissionSessionResponse(BaseModel):
    """Response body for an idempotent respondent session completion."""

    status: Literal["completed"]
    completed_at: datetime
