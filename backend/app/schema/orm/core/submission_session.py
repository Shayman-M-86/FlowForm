import uuid
from datetime import datetime
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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CoreBase

if TYPE_CHECKING:
    from app.schema.orm.core.project_subject import ProjectSubject
    from app.schema.orm.core.response_store import ResponseStore
    from app.schema.orm.core.survey import Survey, SurveyVersion
    from app.schema.orm.core.survey_access import SurveyLink
    from app.schema.orm.core.survey_content import SurveyQuestion


class SubmissionSession(CoreBase):
    """One respondent survey attempt, used to derive response-side locators."""

    __tablename__ = "submission_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    survey_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    survey_version_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    response_store_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("response_stores.id", ondelete="RESTRICT"), nullable=False
    )
    link_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("survey_links.id", ondelete="SET NULL"), nullable=True
    )
    project_subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_subjects.id", ondelete="SET NULL"), nullable=True
    )
    browser_session_token_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, unique=True)
    linkage_key_version: Mapped[int] = mapped_column(SmallInteger, server_default=text("1"), nullable=False)
    session_status: Mapped[str] = mapped_column(Text, server_default=text("'in_progress'"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("id", "survey_version_id", name="uq_submission_sessions_id_survey_version_id"),
        UniqueConstraint("project_id", "id", name="uq_submission_sessions_project_id_id"),
        UniqueConstraint("id", "project_subject_id", name="uq_submission_sessions_id_project_subject_id"),
        CheckConstraint("length(browser_session_token_hash) >= 32", name="browser_session_token_hash_len"),
        CheckConstraint("linkage_key_version > 0", name="linkage_key_version_valid"),
        CheckConstraint(
            "session_status IN ('in_progress', 'completed', 'abandoned')",
            name="session_status_valid",
        ),
        CheckConstraint(
            "(session_status = 'completed') = (completed_at IS NOT NULL)",
            name="completed_at_consistent",
        ),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="completed_at_after_started_at",
        ),
        CheckConstraint("expires_at > started_at", name="expires_at_after_started_at"),
        CheckConstraint("last_activity_at >= started_at", name="last_activity_at_after_started_at"),
        CheckConstraint(
            "completed_at IS NULL OR completed_at <= last_activity_at",
            name="completed_before_last_activity",
        ),
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

    link: Mapped[SurveyLink | None] = relationship("SurveyLink", foreign_keys=[link_id], overlaps="survey")
    project_subject: Mapped[ProjectSubject | None] = relationship(
        "ProjectSubject", foreign_keys=[project_subject_id], overlaps="survey"
    )
    response_store: Mapped[ResponseStore] = relationship("ResponseStore", foreign_keys=[response_store_id])
    survey: Mapped[Survey] = relationship("Survey", foreign_keys=[project_id, survey_id])
    survey_version: Mapped[SurveyVersion] = relationship("SurveyVersion", foreign_keys=[survey_version_id])


class SubmissionEvent(CoreBase):
    """Core-side analytics event for a respondent survey session."""

    __tablename__ = "submission_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    survey_version_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    question_node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('session_started', 'question_viewed', 'answer_saved', 'session_completed')",
            name="event_type_valid",
        ),
        CheckConstraint(
            "event_type NOT IN ('question_viewed', 'answer_saved') OR question_node_id IS NOT NULL",
            name="question_required_for_question_events",
        ),
        CheckConstraint(
            "event_type NOT IN ('session_started', 'session_completed') OR question_node_id IS NULL",
            name="question_absent_for_session_events",
        ),
        ForeignKeyConstraint(
            ["session_id", "survey_version_id"],
            ["submission_sessions.id", "submission_sessions.survey_version_id"],
            ondelete="CASCADE",
            name="fk_submission_events_session_version",
        ),
        ForeignKeyConstraint(
            ["question_node_id"],
            ["survey_questions.id"],
            ondelete="SET NULL",
            name="fk_submission_events_question_node",
        ),
        ForeignKeyConstraint(
            ["survey_version_id", "question_node_id"],
            ["survey_questions.survey_version_id", "survey_questions.id"],
            name="fk_submission_events_question_node_same_version",
        ),
    )

    session: Mapped[SubmissionSession] = relationship("SubmissionSession", foreign_keys=[session_id])
    question: Mapped[SurveyQuestion | None] = relationship("SurveyQuestion", foreign_keys=[question_node_id])
