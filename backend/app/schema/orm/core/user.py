from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Identity, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CoreBase

if TYPE_CHECKING:
    from app.schema.orm.core.project import Project, ProjectMembership


class User(CoreBase):
    """An authenticated user identified by their Auth0 subject."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    auth0_user_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    platform_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    project_memberships: Mapped[list[ProjectMembership]] = relationship(
        "ProjectMembership",
        back_populates="user",
    )
    owned_projects: Mapped[list[Project]] = relationship(
        "Project",
        foreign_keys="[Project.created_by_user_id]",
        back_populates="created_by",
    )
