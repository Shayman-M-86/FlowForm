from __future__ import annotations

from dataclasses import dataclass

from app.schema.orm.core.project import Project
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.survey_access import SurveyLink
from app.schema.orm.core.user import User


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
class SubmissionAccessGrant:
    """Survey/version access granted for a respondent session start."""

    survey: Survey
    published_version: SurveyVersion
    link: SurveyLink | None = None


@dataclass(slots=True)
class BootstrapCurrentUserResult:
    """Result of bootstrapping the authenticated local user."""

    user: User
    created: bool
    default_project: Project | None = None
