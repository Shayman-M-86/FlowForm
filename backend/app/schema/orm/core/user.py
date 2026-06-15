from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Identity, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CoreBase

if TYPE_CHECKING:
    from app.schema.orm.core.project import Project, ProjectMembership


class User(CoreBase):
    """An authenticated user identified by their Auth0 subject."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    public_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True, server_default=text(
            "translate(encode(gen_random_bytes(6), 'base64'), '+/', '-_')"
        ),
    )
    auth0_user_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    platform_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Only necessary constraints live in SQLAlchemy; source of truth is the SQL schema file.
    __table_args__ = (
        UniqueConstraint("id", "email", name="uq_users_id_email"),
    )

    project_memberships: Mapped[list[ProjectMembership]] = relationship(
        "ProjectMembership",
        back_populates="user",
    )
    owned_projects: Mapped[list[Project]] = relationship(
        "Project",
        foreign_keys="[Project.created_by_user_id]",
        back_populates="created_by",
    )
