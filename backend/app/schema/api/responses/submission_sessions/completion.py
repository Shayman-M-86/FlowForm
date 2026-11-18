from __future__ import annotations

from typing import Literal

from app.schema.api.common.base import APIResponseModel
from app.schema.types import Timestamp


class CompleteSubmissionSessionResponse(APIResponseModel):
    """Response body for an idempotent respondent session completion."""

    status: Literal["completed"] = "completed"
    # Preserve the recorded completion time, including on idempotent retries.
    completed_at: Timestamp
