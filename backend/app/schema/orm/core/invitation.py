from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CoreBase
from app.schema.enums import ProjectInvitationStatus

if TYPE_CHECKING:
    from app.schema.orm.core.project import Project, ProjectRole
    from app.schema.orm.core.user import User


class ProjectInvitation(CoreBase):
    """A pending or historical invitation to join a project, keyed by email."""

    __tablename__ = "project_invitations"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    invited_email: Mapped[str] = mapped_column(Text, nullable=False)
    role_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("project_roles.id", ondelete="SET NULL"), nullable=True
    )
    invited_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    invite_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectInvitationStatus] = mapped_column(Text, nullable=False, server_default=text("'pending'"))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Only necessary constraints live in SQLAlchemy; source of truth is the SQL schema file.
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "role_id"],
            ["project_roles.project_id", "project_roles.id"],
            name="fk_project_invitations_role_same_project",
        ),
    )

    project: Mapped[Project] = relationship("Project")
    role: Mapped[ProjectRole | None] = relationship("ProjectRole", foreign_keys=[role_id])
    invited_by: Mapped[User | None] = relationship("User", foreign_keys=[invited_by_user_id])
    accepted_by: Mapped[User | None] = relationship("User", foreign_keys=[accepted_by_user_id])
