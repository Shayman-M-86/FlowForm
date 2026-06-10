from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
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
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'pending'"))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'accepted', 'declined', 'revoked')",
            name="status_valid",
        ),
        # uq_project_invitations_pending_project_email is a partial unique index
        # (WHERE status = 'pending') defined in SQL only — SQLAlchemy __table_args__
        # cannot express partial indexes, so it is not mirrored here.
        CheckConstraint(
            "char_length(btrim(invited_email)) BETWEEN 1 AND 254",
            name="email_len",
        ),
        CheckConstraint(
            "invite_message IS NULL OR char_length(btrim(invite_message)) BETWEEN 1 AND 500",
            name="message_len",
        ),
        CheckConstraint(
            "status <> 'accepted' OR (accepted_by_user_id IS NOT NULL AND accepted_at IS NOT NULL)",
            name="accepted_fields",
        ),
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
