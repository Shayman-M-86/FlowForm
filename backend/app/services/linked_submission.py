from __future__ import annotations

from dataclasses import dataclass, field

from app.schema.orm.core.response_subject_mapping import ResponseSubjectMapping
from app.schema.orm.core.survey_submission import SurveySubmission
from app.schema.orm.core.user import User
from app.schema.orm.response.submission import Submission
from app.schema.orm.response.submission_answer import SubmissionAnswer


@dataclass
class LinkedSubmission:
    """App-level domain object representing a submission that spans both databases.

    Wraps the core registry entry, the response payload record, and optional
    identity / answer data. Business logic should consume this object rather
    than manually stitching the two DB sides together.

    The two ORM rows are joined by the shared integer:
      core.survey_submissions.id  <->  response.submissions.core_submission_id

    Privacy note: ``subject_mapping`` and ``user`` are only populated when the
    caller explicitly asks for identity resolution. The response DB side
    (``response_submission``) never holds a real user_id — only
    ``pseudonymous_subject_id``.
    """

    core_submission: SurveySubmission
    response_submission: Submission
    subject_mapping: ResponseSubjectMapping | None = None
    user: User | None = None
    answers: list[SubmissionAnswer] = field(default_factory=list)
