from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Table,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CoreBase

if TYPE_CHECKING:
    from app.schema.orm.core import Permission, Project, ProjectMembership, ProjectRole, SurveyMembershipRole, User


# Pure join table — no extra columns
project_role_permissions = Table(
    "project_role_permissions",
    CoreBase.metadata,
    Column(
        "role_id",
        BigInteger,
        ForeignKey("project_roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_id",
        BigInteger,
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Project(CoreBase):
    """A top-level container for surveys, roles, and memberships."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    created_by: Mapped[User | None] = relationship("User", foreign_keys=[created_by_user_id])
    
    memberships: Mapped[list[ProjectMembership]] = relationship(
    "ProjectMembership",
    back_populates="project",
)


class ProjectRole(CoreBase):
    """A named role scoped to a project, with an assigned permission set."""

    __tablename__ = "project_roles"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    is_system_role: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("project_id", "id", name="uq_project_roles_project_id_id"),
        UniqueConstraint("project_id", "name", name="uq_project_roles_project_name"),
    )

    permissions: Mapped[list[Permission]] = relationship(
        "Permission",
        secondary=project_role_permissions,
    )


class ProjectMembership(CoreBase):
    """Associates a user with a project, optionally assigning a role."""

    __tablename__ = "project_memberships"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("project_roles.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('active', 'invited')", name="ck_project_memberships_status_valid"),
        UniqueConstraint("user_id", "project_id", name="uq_project_memberships_user_project"),
        UniqueConstraint("project_id", "id", name="uq_project_memberships_project_id_id"),
        ForeignKeyConstraint(
            ["project_id", "role_id"],
            ["project_roles.project_id", "project_roles.id"],
            name="fk_project_memberships_role_same_project",
        ),
    )

    user: Mapped[User] = relationship("User", foreign_keys=[user_id], back_populates="project_memberships")
    project: Mapped[Project] = relationship("Project", foreign_keys=[project_id], back_populates="memberships")
    role: Mapped[ProjectRole | None] = relationship("ProjectRole", foreign_keys=[role_id])
    
    survey_roles: Mapped[list[SurveyMembershipRole]] = relationship(
    "SurveyMembershipRole",
    back_populates="membership",
    overlaps="survey,role,membership_roles",
)
