from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Identity, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CoreBase
from app.schema.types import Auth0UserId, EmailAddress, ProfileName, Timestamp, UserId

if TYPE_CHECKING:
    from app.schema.orm.core.project import Project, ProjectMembership


class User(CoreBase, kw_only=True):
    """An authenticated user identified by their Auth0 subject."""

    __tablename__ = "users"

    id: Mapped[UserId] = mapped_column(BigInteger, Identity(), primary_key=True, init=False)
    public_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        server_default=text("translate(encode(gen_random_bytes(6), 'base64'), '+/', '-_')"),
        init=False,
    )
    auth0_user_id: Mapped[Auth0UserId] = mapped_column(Text, unique=True, nullable=False)
    email: Mapped[EmailAddress] = mapped_column(Text, nullable=False)
    display_name: Mapped[ProfileName | None] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[Timestamp] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, init=False
    )
    platform_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Only necessary constraints live in SQLAlchemy; source of truth is the SQL schema file.
    __table_args__ = (UniqueConstraint("id", "email", name="uq_users_id_email"),)

    project_memberships: Mapped[list[ProjectMembership]] = relationship(
        "ProjectMembership", back_populates="user", init=False
    )
    owned_projects: Mapped[list[Project]] = relationship(
        "Project", foreign_keys="[Project.created_by_user_id]", back_populates="created_by", init=False
    )
