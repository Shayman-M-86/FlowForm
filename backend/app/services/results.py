from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.schema.orm.core.project import Project
from app.schema.orm.core.project_subject import ProjectSubject
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.survey_access import SurveyLink
from app.schema.orm.core.user import User

# Why the server-owned context resolved (or did not resolve) a stable subject.
# Mirrors the precedence in subject-identity-and-access.md §4.1.
SubjectResolutionSource = Literal[
    "assigned_link",
    "authenticated_user",
    "recognition_token",
    "anonymous_created",
    "none",
]


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
class ResolvedProjectSubject:
    """Outcome of resolving a stable subject from server-owned context.

    `subject` is the resolved row (or None when the flow permits untracked
    anonymity); `source` records which precedence rule decided it. Callers that
    expose this to respondents must serialise the safe shape only — never the
    subject id, identity ids, or token hashes (subject-identity-and-access.md §6.2).
    """

    subject: ProjectSubject | None
    source: SubjectResolutionSource


@dataclass(slots=True)
class BootstrapCurrentUserResult:
    """Result of bootstrapping the authenticated local user."""

    user: User
    created: bool
    default_project: Project | None = None
