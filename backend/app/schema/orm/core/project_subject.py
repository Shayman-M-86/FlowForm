import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CoreBase

if TYPE_CHECKING:
    from app.schema.orm.core.project import Project
    from app.schema.orm.core.user import User


class ProjectSubject(CoreBase):
    """A pseudonymous participant identity, optionally linked to a known user, within one project."""

    __tablename__ = "project_subjects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    pseudonymous_subject_id: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("project_id", "id", name="uq_project_subjects_project_id_id"),
        UniqueConstraint(
            "project_id", "pseudonymous_subject_id", name="uq_project_subjects_project_id_pseudonymous_subject_id"
        ),
        UniqueConstraint("project_id", "user_id", name="uq_project_subjects_project_id_user_id"),
        CheckConstraint(
            "char_length(btrim(pseudonymous_subject_id)) BETWEEN 1 AND 128",
            name="pseudonymous_subject_id_len",
        ),
    )

    project: Mapped[Project] = relationship("Project", foreign_keys=[project_id])
    user: Mapped[User | None] = relationship("User", foreign_keys=[user_id])
