import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CoreBase

if TYPE_CHECKING:
    from app.models.core.project import Project
    from app.models.core.user import User


class ResponseSubjectMapping(CoreBase):
    """Maps an authenticated user to a stable pseudonymous identifier per project."""

    __tablename__ = "response_subject_mappings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    pseudonymous_subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("project_id", "id", name="uq_response_subject_mappings_project_id"),
        UniqueConstraint("project_id", "user_id", name="uq_response_subject_mappings_project_user"),
        UniqueConstraint("project_id", "pseudonymous_subject_id", name="uq_response_subject_mappings_project_subject"),
    )

    project: Mapped[Project] = relationship("Project", foreign_keys=[project_id])
    user: Mapped[User] = relationship("User", foreign_keys=[user_id])
