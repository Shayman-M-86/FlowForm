from app.schema.orm.core.submission_session import SubmissionEvent
from app.schema.orm.response.response_answer import ResponseAnswer
from app.schema.orm.response.response_envelope import ResponseEnvelope

# TEMP(rework): Package-level legacy aliases for old response ORM names.
# Remove these after consumers switch to ResponseEnvelope/ResponseAnswer.
Submission = ResponseEnvelope
SubmissionAnswer = ResponseAnswer

__all__ = [
    "ResponseAnswer",
    "ResponseEnvelope",
    "Submission",
    "SubmissionAnswer",
    "SubmissionEvent",
]
