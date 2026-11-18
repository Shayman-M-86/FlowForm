from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    LargeBinary,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CoreBase
from app.schema.enums import SubmissionEventType, SubmissionSessionStatus
from app.schema.models.common.types import Timestamp
from app.schema.models.projects.types import ProjectId, SubjectId
from app.schema.models.response_store.types import ResponseStoreId
from app.schema.models.submission.types import SubmissionSessionId
from app.schema.models.survey.types import SurveyFieldUuid, SurveyId, SurveyLinkId, SurveyVersionId
from app.schema.orm.base import utc_now

if TYPE_CHECKING:
    from app.schema.orm.core.project_subject import ProjectSubject
    from app.schema.orm.core.response_store import ResponseStore
    from app.schema.orm.core.survey import Survey, SurveyVersion
    from app.schema.orm.core.survey_access import SurveyLink


@dataclass(frozen=True, slots=True)
class SessionRef:
    """Scalar session fields needed by crypto/session locator services."""

    id: SubmissionSessionId
    project_id: ProjectId
    survey_id: SurveyId
    survey_version_id: SurveyVersionId
    expires_at: Timestamp
    browser_session_token_hash: bytes


class SubmissionSession(CoreBase, kw_only=True):
    """One respondent survey attempt, used to derive response-side locators."""

    __tablename__ = "submission_sessions"

    id: Mapped[SubmissionSessionId] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(), init=False
    )
    project_id: Mapped[ProjectId] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    survey_id: Mapped[SurveyId] = mapped_column(BigInteger, nullable=False)
    survey_version_id: Mapped[SurveyVersionId] = mapped_column(BigInteger, nullable=False)
    response_store_id: Mapped[ResponseStoreId] = mapped_column(
        BigInteger, ForeignKey("response_stores.id", ondelete="RESTRICT"), nullable=False
    )
    link_id: Mapped[SurveyLinkId | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("survey_links.id", ondelete="SET NULL"), nullable=True, default=None
    )
    project_subject_id: Mapped[SubjectId | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_subjects.id", ondelete="SET NULL"), nullable=True, default=None
    )
    browser_session_token_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, unique=True)
    linkage_key_version: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("linkage_key_versions.version"), nullable=False
    )
    session_status: Mapped[SubmissionSessionStatus] = mapped_column(
        Text, server_default=text("'in_progress'"), nullable=False, default="in_progress"
    )
    started_at: Mapped[Timestamp] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, default_factory=utc_now
    )
    completed_at: Mapped[Timestamp | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    expires_at: Mapped[Timestamp] = mapped_column(DateTime(timezone=True), nullable=False)
    last_activity_at: Mapped[Timestamp] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, default_factory=utc_now
    )

    # Only necessary constraints live in SQLAlchemy; source of truth is the SQL schema file.
    __table_args__ = (
        UniqueConstraint("id", "survey_version_id", name="uq_submission_sessions_id_survey_version_id"),
        UniqueConstraint("project_id", "id", name="uq_submission_sessions_project_id_id"),
        UniqueConstraint("id", "project_subject_id", name="uq_submission_sessions_id_project_subject_id"),
        ForeignKeyConstraint(
            ["project_id", "survey_id"],
            ["surveys.project_id", "surveys.id"],
            ondelete="CASCADE",
            name="fk_submission_sessions_survey_same_project",
        ),
        ForeignKeyConstraint(
            ["survey_id", "survey_version_id"],
            ["survey_versions.survey_id", "survey_versions.id"],
            ondelete="RESTRICT",
            name="fk_submission_sessions_version_same_survey",
        ),
        ForeignKeyConstraint(
            ["project_id", "response_store_id"],
            ["response_stores.project_id", "response_stores.id"],
            name="fk_submission_sessions_store_same_project",
        ),
        ForeignKeyConstraint(
            ["survey_id", "link_id"],
            ["survey_links.survey_id", "survey_links.id"],
            name="fk_submission_sessions_link_same_survey",
        ),
        ForeignKeyConstraint(
            ["project_id", "project_subject_id"],
            ["project_subjects.project_id", "project_subjects.id"],
            name="fk_submission_sessions_project_subject_same_project",
        ),
    )

    link: Mapped[SurveyLink | None] = relationship("SurveyLink", foreign_keys=[link_id], overlaps="survey", init=False)
    project_subject: Mapped[ProjectSubject | None] = relationship(
        "ProjectSubject", foreign_keys=[project_subject_id], overlaps="survey", init=False
    )
    response_store: Mapped[ResponseStore] = relationship("ResponseStore", foreign_keys=[response_store_id], init=False)
    survey: Mapped[Survey] = relationship("Survey", foreign_keys=[project_id, survey_id], init=False)
    survey_version: Mapped[SurveyVersion] = relationship("SurveyVersion", foreign_keys=[survey_version_id], init=False)

    def to_crypto_ref(self) -> SessionRef:
        """Return a scalar-only snapshot for crypto/session locator services."""
        return SessionRef(
            id=self.id,
            project_id=self.project_id,
            survey_id=self.survey_id,
            survey_version_id=self.survey_version_id,
            expires_at=self.expires_at,
            browser_session_token_hash=self.browser_session_token_hash,
        )


class SubmissionEvent(CoreBase, kw_only=True):
    """Core-side analytics event for a respondent survey session."""

    __tablename__ = "submission_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(), init=False
    )
    session_id: Mapped[SubmissionSessionId] = mapped_column(UUID(as_uuid=True), nullable=False)
    survey_version_id: Mapped[SurveyVersionId] = mapped_column(BigInteger, nullable=False)
    event_type: Mapped[SubmissionEventType] = mapped_column(Text, nullable=False)
    field_uuid: Mapped[SurveyFieldUuid | None] = mapped_column(UUID(as_uuid=True), nullable=True, default=None)
    event_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True, default=None)
    received_at: Mapped[Timestamp] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, init=False
    )

    # Only necessary constraints live in SQLAlchemy; source of truth is the SQL schema file.
    __table_args__ = (
        CheckConstraint(
            "metadata IS NULL OR jsonb_typeof(metadata) = 'object'", name="ck_submission_events_metadata_is_object"
        ),
        ForeignKeyConstraint(
            ["session_id", "survey_version_id"],
            ["submission_sessions.id", "submission_sessions.survey_version_id"],
            ondelete="CASCADE",
            name="fk_submission_events_session_version",
        ),
    )

    session: Mapped[SubmissionSession] = relationship("SubmissionSession", foreign_keys=[session_id], init=False)
