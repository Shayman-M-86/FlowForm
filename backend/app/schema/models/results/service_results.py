"""Internal service outcomes and result carriers, separate from HTTP contracts.

Dataclasses preserve existing construction and workflow behavior. ORM references
are imported only for static checking, so importing these models does not load
persistence mappings. Legacy admin/export fields remain explicit until those
producers are migrated to the V2 document model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

from pydantic import BaseModel

from app.schema.enums import (
    SubjectResolutionSource,
    SubmissionAccessMethod,
    SubmissionAnswerState,
    SubmissionEventType,
    SubmissionSessionStatus,
    TokenAction,
)
from app.schema.models.survey_document.answer_value import AnswerValue
from app.schema.types import (
    Count,
    PageNumber,
    PageSize,
    ProjectId,
    ReadableId,
    ResponseStoreId,
    SubjectCode,
    SubjectId,
    SubmissionSessionId,
    SurveyId,
    SurveyLinkId,
    SurveyVersionId,
    Timestamp,
)

if TYPE_CHECKING:
    from app.schema.orm.core.project import Project
    from app.schema.orm.core.project_subject import ProjectSubject
    from app.schema.orm.core.submission_session import SubmissionSession
    from app.schema.orm.core.survey import Survey, SurveyVersion
    from app.schema.orm.core.survey_access import SurveyLink
    from app.schema.orm.core.user import User

# Existing export labels, retained locally rather than resurrecting a shared
# node-era enum or importing deleted API answer schemas.
type LegacyAnswerFamily = Literal["choice", "field", "matching", "rating"]

# Account outcomes


@dataclass(slots=True)
class BootstrapCurrentUserResult:
    """Result of bootstrapping the authenticated local user."""

    user: User
    created: bool
    default_project: Project | None = None


# Survey discovery outcomes


@dataclass(slots=True)
class GetPublicSurveyResult:
    """Result returned by PublicSurveyService.get_public_survey."""

    survey: Survey
    published_version: SurveyVersion | None


@dataclass(slots=True)
class ListPublicSurveysResult:
    """Result returned by PublicSurveyService.list_public_surveys."""

    surveys: list[Survey]
    total: Count
    page: PageNumber
    page_size: PageSize


@dataclass(slots=True)
class ResolveLinkResult:
    """Result of resolving a respondent survey access link token."""

    link: SurveyLink
    survey: Survey
    published_version: SurveyVersion


# Submission workflow outcomes


@dataclass(slots=True)
class RecognitionTokenLookupResult:
    """Candidate token metadata from check-recognition-token sub-flow.

    Lookup only — does not decide final subject or update last_used_at.
    Docs: Flows/shared/check-recognition-token.md
    """

    token_present: bool
    token_valid: bool
    token_id: UUID | None = None
    token_subject_id: SubjectId | None = None
    canonical_token_subject_id: SubjectId | None = None
    invalid_reason: str | None = None


@dataclass(slots=True)
class SubmissionAccessGrant:
    """Validated access context for respondent survey entry."""

    access_method: SubmissionAccessMethod
    project_id: ProjectId
    survey_id: SurveyId
    survey_version_id: SurveyVersionId
    response_store_id: ResponseStoreId
    requires_auth: bool
    is_single_use: bool
    survey: Survey
    published_version: SurveyVersion
    link_id: SurveyLinkId | None = None
    assigned_subject_id: SubjectId | None = None
    link: SurveyLink | None = None


@dataclass(slots=True)
class SubjectResolutionResult:
    """Outcome of subject-resolution including required token and merge instructions.

    Callers apply merge writes and token mechanics before committing the session.
    Docs: Flows/shared/subject-resolution.md
    """

    final_subject_id: SubjectId
    subject_code: SubjectCode
    subject_source: SubjectResolutionSource
    token_action: TokenAction
    needs_identity_write: bool = False
    merge_subject_id: SubjectId | None = None
    merge_into_subject_id: SubjectId | None = None


@dataclass(slots=True)
class AccountLinkingResult:
    """Result of the authenticated account-linking endpoint.

    raw_recognition_token is set only when a browser token was rotated so the
    caller can update the recognition cookie. None means the cookie is unchanged.
    Docs: Authenticated-link-access-Flow.md §5 — Recognition token reconciliation
    """

    link: SurveyLink
    raw_recognition_token: str | None


@dataclass(frozen=True, slots=True)
class AnswerSaveResult:
    """Result of saving a respondent answer."""

    node_key: ReadableId


@dataclass(frozen=True, slots=True)
class DeletionResult:
    """Outcome of a response deletion attempt."""

    session_id: SubmissionSessionId
    response_deleted: bool
    core_deleted: bool


# Existing admin result trees and exports


@dataclass(frozen=True, slots=True)
class AnswerSlotResult:
    """One answer slot, optionally with its decrypted value."""

    slot_id: UUID
    question_node_id: UUID
    question_key: ReadableId | None
    answer_family: LegacyAnswerFamily | None
    has_encrypted_answer: bool
    decrypted: bool
    answer_state: SubmissionAnswerState | None
    answer_value: AnswerValue | dict[str, Any] | None
    question_content: dict[str, Any] | None = None
    question_sort_key: int | None = None


@dataclass(frozen=True, slots=True)
class SessionEventResult:
    """One timeline event for a session (no answer values)."""

    event_type: SubmissionEventType
    question_node_id: UUID | None
    received_at: Timestamp


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

    session_id: SubmissionSessionId
    status: SubmissionSessionStatus
    started_at: Timestamp
    completed_at: Timestamp | None
    question_key: ReadableId | None = None
    answer_family: LegacyAnswerFamily | None = None
    has_encrypted_answer: bool | None = None
    decrypted: bool | None = None
    answer_state: SubmissionAnswerState | None = None
    answer_value: AnswerValue | dict[str, Any] | None = None

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
