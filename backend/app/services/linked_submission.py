from dataclasses import dataclass, field

from app.schema.orm.core.response_subject_mapping import ResponseSubjectMapping
from app.schema.orm.core.survey_submission import SurveySubmission
from app.schema.orm.core.user import User
from app.schema.orm.response.submission import Submission
from app.schema.orm.response.submission_answer import SubmissionAnswer


@dataclass
class LinkedSubmission:
    """Domain object wrapping both DB sides of a submission."""

    core_submission: SurveySubmission
    response_submission: Submission | None
    subject_mapping: ResponseSubjectMapping | None
    user: User | None
    answers: list[SubmissionAnswer] = field(default_factory=list)
