from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

from app.schema.api.submission_sessions.answer_payload import SubmissionAnswerValue
from app.schema.enums import (
    AnswerFamily,
    SubmissionAnswerState,
    SubmissionEventType,
    SubmissionSessionStatus,
)
from app.schema.orm.core.project import Project
from app.schema.orm.core.project_subject import ProjectSubject
from app.schema.orm.core.submission_session import SubmissionSession
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
class ResolveLinkResult:
    """Result of resolving a respondent survey access link token."""

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
    response_store_id: int
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
    subject_code: str
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


@dataclass(frozen=True, slots=True)
class AnswerSaveResult:
    """Result of saving a respondent answer."""

    node_key: str


@dataclass(frozen=True, slots=True)
class AnswerSlotResult:
    """One answer slot, optionally with its decrypted value."""

    slot_id: UUID
    question_node_id: UUID
    question_key: str | None
    answer_family: AnswerFamily | None
    has_encrypted_answer: bool
    decrypted: bool
    answer_state: SubmissionAnswerState | None
    answer_value: SubmissionAnswerValue | dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class SessionEventResult:
    """One timeline event for a session (no answer values)."""

    event_type: SubmissionEventType
    question_node_id: UUID | None
    received_at: datetime


@dataclass(frozen=True, slots=True)
class SessionTreeResult:
    """One session with its answer slots and optional event timeline."""

    session: SubmissionSession
    answers: list[AnswerSlotResult]
    events: list[SessionEventResult] | None = None


@dataclass(frozen=True, slots=True)
class SubjectTreeResult:
    """A subject with all of its sessions for one survey."""

    subject: ProjectSubject
    sessions: list[SessionTreeResult]


@dataclass(frozen=True, slots=True)
class ExportRow:
    """One flat row in a survey-results export, one per answer slot (or per session if none)."""

    session_id: UUID
    status: SubmissionSessionStatus
    started_at: datetime
    completed_at: datetime | None
    question_key: str | None = None
    answer_family: AnswerFamily | None = None
    has_encrypted_answer: bool | None = None
    decrypted: bool | None = None
    answer_state: SubmissionAnswerState | None = None
    answer_value: SubmissionAnswerValue | dict[str, Any] | None = None

    def to_json_dict(self) -> dict[str, Any]:
        """Flatten to a JSON/CSV-safe dict, normalising the answer_value union."""
        answer_value: Any = self.answer_value
        if isinstance(answer_value, BaseModel):
            answer_value = answer_value.model_dump(mode="json")
        return {
            "session_id": str(self.session_id),
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "question_key": self.question_key,
            "answer_family": self.answer_family,
            "has_encrypted_answer": self.has_encrypted_answer,
            "decrypted": self.decrypted,
            "answer_state": self.answer_state,
            "answer_value": answer_value,
        }


@dataclass(frozen=True, slots=True)
class ExportFile:
    """A fully-formatted export file body, ready to stream as an HTTP response."""

    body: str
    mimetype: str
    filename: str


@dataclass(frozen=True, slots=True)
class DeletionResult:
    """Outcome of a response deletion attempt."""

    session_id: UUID
    response_deleted: bool
    core_deleted: bool
