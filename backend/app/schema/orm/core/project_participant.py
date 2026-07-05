import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CoreBase

if TYPE_CHECKING:
    from app.schema.orm.core.project import Project
    from app.schema.orm.core.project_subject import ProjectSubject, ProjectSubjectIdentity


class ProjectParticipant(CoreBase):
    """A subject enrolled in a project under a specific identity.

    A participant always carries both a subject and one of that subject's
    identities (enforced by a composite FK), so a survey link can reach a
    subject + identity through the participant alone.
    """

    __tablename__ = "project_participants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    project_subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    identity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Only necessary constraints live in SQLAlchemy; source of truth is the SQL schema file.
    __table_args__ = (
        UniqueConstraint("project_id", "project_subject_id", name="uq_project_participants_project_subject"),
        # Composite UNIQUE that survey_links' assigned_participant FK targets.
        UniqueConstraint("project_id", "id", name="uq_project_participants_project_id_id"),
        ForeignKeyConstraint(
            ["project_id", "project_subject_id"],
            ["project_subjects.project_id", "project_subjects.id"],
            ondelete="CASCADE",
            name="fk_project_participants_subject_same_project",
        ),
        # The participant's identity must belong to the participant's subject in
        # the same project.
        ForeignKeyConstraint(
            ["project_id", "project_subject_id", "identity_id"],
            [
                "project_subject_identities.project_id",
                "project_subject_identities.project_subject_id",
                "project_subject_identities.id",
            ],
            ondelete="CASCADE",
            name="fk_project_participants_identity_same_subject",
        ),
    )

    project: Mapped[Project] = relationship("Project", foreign_keys=[project_id])
    subject: Mapped[ProjectSubject] = relationship(
        "ProjectSubject",
        foreign_keys=[project_id, project_subject_id],
        overlaps="project",
    )
    identity: Mapped[ProjectSubjectIdentity] = relationship(
        "ProjectSubjectIdentity",
        foreign_keys=[project_id, project_subject_id, identity_id],
        overlaps="project,subject",
    )
