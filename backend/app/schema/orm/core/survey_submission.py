"""Temporary compatibility import for the response-infrastructure rework."""

from app.schema.orm.core.submission_session import SubmissionSession

# TEMP(rework): Legacy imports still ask for SurveySubmission while the
# submission registry is being replaced by SubmissionSession.
# Remove this alias after services/tests import SubmissionSession directly.
SurveySubmission = SubmissionSession

__all__ = ["SurveySubmission"]
