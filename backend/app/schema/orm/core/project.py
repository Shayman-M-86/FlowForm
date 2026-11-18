from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
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
from app.schema.enums import ProjectMemberStatus
from app.schema.models.common.types import Slug, Timestamp
from app.schema.models.identity.types import UserId
from app.schema.models.projects.types import (
    ProjectId,
    ProjectMembershipId,
    ProjectName,
    ProjectRoleId,
    RoleDescription,
    RoleName,
)

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


class Project(CoreBase, kw_only=True):
    """A top-level container for surveys, roles, and memberships."""

    __tablename__ = "projects"

    id: Mapped[ProjectId] = mapped_column(BigInteger, Identity(), primary_key=True, init=False)
    name: Mapped[ProjectName] = mapped_column(Text, nullable=False)
    slug: Mapped[Slug] = mapped_column(Text, unique=True, nullable=False)
    created_by_user_id: Mapped[UserId | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, default=None
    )
    created_at: Mapped[Timestamp] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, init=False
    )

    created_by: Mapped[User | None] = relationship("User", foreign_keys=[created_by_user_id], init=False)

    memberships: Mapped[list[ProjectMembership]] = relationship(
        "ProjectMembership", back_populates="project", init=False
    )


class ProjectRole(CoreBase, kw_only=True):
    """A named role scoped to a project, with an assigned permission set."""

    __tablename__ = "project_roles"

    id: Mapped[ProjectRoleId] = mapped_column(BigInteger, Identity(), primary_key=True, init=False)
    project_id: Mapped[ProjectId] = mapped_column(
        BigInteger,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[RoleName] = mapped_column(Text, nullable=False)
    description: Mapped[RoleDescription | None] = mapped_column(Text, nullable=True, default=None)
    is_system_role: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"), default=False)
    created_at: Mapped[Timestamp] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), init=False
    )

    # Only necessary constraints live in SQLAlchemy; source of truth is the SQL schema file.
    __table_args__ = (UniqueConstraint("project_id", "id", name="uq_project_roles_project_id_id"),)

    permissions: Mapped[list[Permission]] = relationship("Permission", secondary=project_role_permissions, init=False)


class ProjectMembership(CoreBase, kw_only=True):
    """Associates a user with a project, optionally assigning a role."""

    __tablename__ = "project_memberships"

    id: Mapped[ProjectMembershipId] = mapped_column(BigInteger, Identity(), primary_key=True, init=False)
    user_id: Mapped[UserId] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[ProjectId] = mapped_column(
        BigInteger,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id: Mapped[ProjectRoleId | None] = mapped_column(
        BigInteger, ForeignKey("project_roles.id", ondelete="SET NULL"), nullable=True, default=None
    )
    status: Mapped[ProjectMemberStatus] = mapped_column(
        Text, nullable=False, server_default=text("'active'"), default="active"
    )
    created_at: Mapped[Timestamp] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), init=False
    )

    # Only necessary constraints live in SQLAlchemy; source of truth is the SQL schema file.
    __table_args__ = (
        UniqueConstraint("project_id", "id", name="uq_project_memberships_project_id_id"),
        ForeignKeyConstraint(
            ["project_id", "role_id"],
            ["project_roles.project_id", "project_roles.id"],
            name="fk_project_memberships_role_same_project",
        ),
    )

    user: Mapped[User] = relationship("User", foreign_keys=[user_id], back_populates="project_memberships", init=False)
    project: Mapped[Project] = relationship(
        "Project", foreign_keys=[project_id], back_populates="memberships", init=False
    )
    role: Mapped[ProjectRole | None] = relationship("ProjectRole", foreign_keys=[role_id], init=False)

    survey_roles: Mapped[list[SurveyMembershipRole]] = relationship(
        "SurveyMembershipRole", back_populates="membership", overlaps="survey,role,membership_roles", init=False
    )
