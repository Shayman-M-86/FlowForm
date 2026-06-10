"""Temporary compatibility import for the response-infrastructure rework."""

from app.schema.orm.core.submission_session import SubmissionEvent

# TEMP(rework): Legacy imports still expect response-side SubmissionEvent.
# Events now live in the core submission-session model during this rework.
# Remove this module after services/tests import the core event directly.
__all__ = ["SubmissionEvent"]
