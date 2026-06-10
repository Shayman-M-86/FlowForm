"""Temporary compatibility import for the response-infrastructure rework."""

from app.schema.orm.response.response_envelope import ResponseEnvelope

# TEMP(rework): Legacy imports still ask for Submission while the response DB
# is being replaced by encrypted ResponseEnvelope/ResponseAnswer rows.
# Remove this alias after services/tests import ResponseEnvelope directly.
Submission = ResponseEnvelope

__all__ = ["Submission"]
