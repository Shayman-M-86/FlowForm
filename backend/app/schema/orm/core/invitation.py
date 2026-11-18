from __future__ import annotations

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
from app.schema.types import (
    EmailAddress,
    InvitationMessage,
    ProjectId,
    ProjectInvitationId,
    ProjectRoleId,
    Timestamp,
    UserId,
)

if TYPE_CHECKING:
    from app.schema.orm.core.project import Project, ProjectRole
    from app.schema.orm.core.user import User


class ProjectInvitation(CoreBase, kw_only=True):
    """A pending or historical invitation to join a project, keyed by email."""

    __tablename__ = "project_invitations"

    id: Mapped[ProjectInvitationId] = mapped_column(BigInteger, Identity(), primary_key=True, init=False)
    project_id: Mapped[ProjectId] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    invited_email: Mapped[EmailAddress] = mapped_column(Text, nullable=False)
    role_id: Mapped[ProjectRoleId | None] = mapped_column(
        BigInteger, ForeignKey("project_roles.id", ondelete="SET NULL"), nullable=True, default=None
    )
    invited_by_user_id: Mapped[UserId | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, default=None
    )
    invite_message: Mapped[InvitationMessage | None] = mapped_column(Text, nullable=True, default=None)
    status: Mapped[ProjectInvitationStatus] = mapped_column(
        Text, nullable=False, default="pending", server_default=text("'pending'")
    )
    expires_at: Mapped[Timestamp | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    accepted_by_user_id: Mapped[UserId | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, default=None
    )
    accepted_at: Mapped[Timestamp | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[Timestamp] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, init=False
    )

    # Only necessary constraints live in SQLAlchemy; source of truth is the SQL schema file.
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "role_id"],
            ["project_roles.project_id", "project_roles.id"],
            name="fk_project_invitations_role_same_project",
        ),
    )

    project: Mapped[Project] = relationship("Project", init=False)
    role: Mapped[ProjectRole | None] = relationship("ProjectRole", foreign_keys=[role_id], init=False)
    invited_by: Mapped[User | None] = relationship("User", foreign_keys=[invited_by_user_id], init=False)
    accepted_by: Mapped[User | None] = relationship("User", foreign_keys=[accepted_by_user_id], init=False)
