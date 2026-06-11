import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CoreBase

if TYPE_CHECKING:
    from app.schema.orm.core.project import Project
    from app.schema.orm.core.project_subject import ProjectSubject
    from app.schema.orm.core.submission_session import SubmissionSession


class SubjectIpObservation(CoreBase):
    """Project-scoped IP observation tied to a subject and/or a session.

    IP addresses are identifying core metadata and must never cross into the
    response database; the application applies an explicit retention policy.
    """

    __tablename__ = "subject_ip_observations"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    project_subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_subjects.id", ondelete="CASCADE"), nullable=True
    )
    submission_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("submission_sessions.id", ondelete="CASCADE"), nullable=True
    )
    ip_address: Mapped[str] = mapped_column(INET, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "project_subject_id IS NOT NULL OR submission_session_id IS NOT NULL",
            name="has_owner",
        ),
        ForeignKeyConstraint(
            ["project_id", "project_subject_id"],
            ["project_subjects.project_id", "project_subjects.id"],
            name="fk_subject_ip_observations_subject_same_project",
        ),
        ForeignKeyConstraint(
            ["project_id", "submission_session_id"],
            ["submission_sessions.project_id", "submission_sessions.id"],
            name="fk_subject_ip_observations_session_same_project",
        ),
        # When both are populated, the observation subject must match the
        # subject attached to the session.
        ForeignKeyConstraint(
            ["submission_session_id", "project_subject_id"],
            ["submission_sessions.id", "submission_sessions.project_subject_id"],
            name="fk_subject_ip_observations_session_subject_match",
        ),
        Index(
            "ix_subject_ip_observations_project_observed_at",
            "project_id",
            text("observed_at DESC"),
        ),
        Index(
            "ix_subject_ip_observations_subject_observed_at",
            "project_subject_id",
            text("observed_at DESC"),
            postgresql_where=text("project_subject_id IS NOT NULL"),
        ),
        Index(
            "ix_subject_ip_observations_session_observed_at",
            "submission_session_id",
            text("observed_at DESC"),
            postgresql_where=text("submission_session_id IS NOT NULL"),
        ),
        Index(
            "ix_subject_ip_observations_ip_observed_at",
            "ip_address",
            text("observed_at DESC"),
        ),
    )

    project: Mapped[Project] = relationship("Project", foreign_keys=[project_id], overlaps="subject,session")
    subject: Mapped[ProjectSubject | None] = relationship(
        "ProjectSubject",
        foreign_keys=[project_id, project_subject_id],
        overlaps="project,session",
    )
    session: Mapped[SubmissionSession | None] = relationship(
        "SubmissionSession",
        foreign_keys=[project_id, submission_session_id],
        overlaps="project,subject",
    )
