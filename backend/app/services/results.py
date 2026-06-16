from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

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
SubmissionAccessMethod = Literal[
    "public_slug",
    "general_link",
    "private_link",
    "authenticated_assigned_link",
]


@dataclass(slots=True)
class RecognitionTokenLookupResult:
    """Candidate token metadata from check-recognition-token sub-flow.

    Lookup only — does not decide final subject or update last_used_at.
    Docs: Flows/shared/check-recognition-token.md
    """

    token_present: bool
    token_valid: bool
    token_id: UUID | None = None
    token_subject_id: UUID | None = None
    canonical_token_subject_id: UUID | None = None
    invalid_reason: str | None = None


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
    """Validated access context for respondent survey entry."""

    access_method: SubmissionAccessMethod
    project_id: int
    survey_id: int
    survey_version_id: int
    requires_auth: bool
    is_single_use: bool
    survey: Survey
    published_version: SurveyVersion
    link_id: UUID | None = None
    assigned_subject_id: UUID | None = None
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


TokenAction = Literal["issue", "rotate", "keep", "mark_used", "none"]


@dataclass(slots=True)
class SubjectResolutionResult:
    """Outcome of subject-resolution including required token and merge instructions.

    Callers apply merge writes and token mechanics before committing the session.
    Docs: Flows/shared/subject-resolution.md
    """

    final_subject_id: UUID
    subject_source: SubjectResolutionSource
    token_action: TokenAction
    needs_identity_write: bool = False
    merge_subject_id: UUID | None = None
    merge_into_subject_id: UUID | None = None


@dataclass(slots=True)
class AccountLinkingResult:
    """Result of the authenticated account-linking endpoint.

    raw_recognition_token is set only when a browser token was rotated so the
    caller can update the recognition cookie. None means the cookie is unchanged.
    Docs: Authenticated-link-access-Flow.md §5 — Recognition token reconciliation
    """

    link: SurveyLink
    raw_recognition_token: str | None


@dataclass(slots=True)
class BootstrapCurrentUserResult:
    """Result of bootstrapping the authenticated local user."""

    user: User
    created: bool
    default_project: Project | None = None
