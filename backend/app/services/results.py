from dataclasses import dataclass, field

from app.schema.orm.core.response_subject_mapping import ResponseSubjectMapping
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.survey_access import SurveyLink
from app.schema.orm.core.survey_submission import SurveySubmission
from app.schema.orm.core.user import User
from app.schema.orm.response.submission import Submission
from app.schema.orm.response.submission_answer import SubmissionAnswer


@dataclass
class LinkedSubmissionResult:
    """Domain object wrapping both DB sides of a submission."""

    core_submission: SurveySubmission
    response_submission: Submission | None
    subject_mapping: ResponseSubjectMapping | None
    user: User | None
    answers: list[SubmissionAnswer] = field(default_factory=list)


@dataclass(slots=True)
class GetPublicSurveyResult:
    """Result returned by PublicSurveyService.get_public_survey."""

    survey: Survey
    published_version: SurveyVersion | None


@dataclass(slots=True)
class ListPublicSurveysResult:
    """Result returned by PublicSurveyService.list_public_surveys."""

    surveys: list[Survey]
    total: int
    page: int
    page_size: int


@dataclass(slots=True)
class CreatePublicLinkResult:
    """Result of creating a public link."""

    link: SurveyLink
    token: str


@dataclass(slots=True)
class ResolveLinkResult:
    """Result of resolving a public link token."""

    link: SurveyLink
    survey: Survey
    published_version: SurveyVersion


@dataclass(slots=True)
class BootstrapCurrentUserResult:
    """Result of bootstrapping the authenticated local user."""

    user: User
    created: bool
