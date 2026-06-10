"""Temporary compatibility import for the response-infrastructure rework."""

from app.schema.orm.response.response_answer import ResponseAnswer

# TEMP(rework): Legacy imports still ask for SubmissionAnswer while response
# answers are being replaced by encrypted ResponseAnswer rows plus revisions.
# Remove this alias after services/tests import ResponseAnswer directly.
SubmissionAnswer = ResponseAnswer

__all__ = ["SubmissionAnswer"]
