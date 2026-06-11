import uuid
from datetime import datetime
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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CoreBase

if TYPE_CHECKING:
    from app.schema.orm.core.permission import Permission
    from app.schema.orm.core.project import Project, ProjectMembership
    from app.schema.orm.core.project_subject import ProjectSubject
    from app.schema.orm.core.survey import Survey

# Pure join table — no extra columns
survey_role_permissions = Table(
    "survey_role_permissions",
    CoreBase.metadata,
    Column(
        "role_id",
        BigInteger,
        ForeignKey("survey_roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_id",
        BigInteger,
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class SurveyRole(CoreBase):
    """A survey-level role override scoped to a project."""

    __tablename__ = "survey_roles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Only necessary constraints live in SQLAlchemy; source of truth is the SQL schema file.
    __table_args__ = (
        UniqueConstraint("project_id", "id", name="uq_survey_roles_project_id_id"),
    )

    permissions: Mapped[list[Permission]] = relationship("Permission", secondary=survey_role_permissions)
    
    membership_roles: Mapped[list[SurveyMembershipRole]] = relationship(
    "SurveyMembershipRole",
    back_populates="role",
    overlaps="survey,membership",
)


class SurveyMembershipRole(CoreBase):
    """Assigns a survey-level role to a project membership for a specific survey."""

    __tablename__ = "survey_membership_roles"

    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    survey_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    membership_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "survey_id"],
            ["surveys.project_id", "surveys.id"],
            ondelete="CASCADE",
            name="fk_survey_membership_roles_survey_same_project",
        ),
        ForeignKeyConstraint(
            ["project_id", "membership_id"],
            ["project_memberships.project_id", "project_memberships.id"],
            ondelete="CASCADE",
            name="fk_survey_membership_roles_membership_same_project",
        ),
        ForeignKeyConstraint(
            ["project_id", "role_id"],
            ["survey_roles.project_id", "survey_roles.id"],
            ondelete="CASCADE",
            name="fk_survey_membership_roles_role_same_project",
        ),
    )
    survey: Mapped[Survey] = relationship(
    "Survey",
    overlaps="membership,role,membership_roles,survey_roles",
    )

    membership: Mapped[ProjectMembership] = relationship(
    "ProjectMembership",
    back_populates="survey_roles",
    overlaps="survey,role,membership_roles",
    )

    role: Mapped[SurveyRole] = relationship(
    "SurveyRole",
    back_populates="membership_roles",
    overlaps="survey,membership,survey_roles",
    )


class SurveyLink(CoreBase):
    """Bearer-token link granting survey access.

    project_id is stored directly so the database can prove the link, its survey,
    and its assigned subject all belong to the same project. token_hash is a
    lowercase hex SHA-256 digest.
    """

    __tablename__ = "survey_links"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    survey_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    token_prefix: Mapped[str] = mapped_column(Text, nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    requires_auth: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    assigned_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Only necessary constraints live in SQLAlchemy; source of truth is the SQL schema file.
    __table_args__ = (
        UniqueConstraint("survey_id", "id", name="uq_survey_links_survey_id_id"),
        ForeignKeyConstraint(
            ["project_id", "survey_id"],
            ["surveys.project_id", "surveys.id"],
            ondelete="CASCADE",
            name="fk_survey_links_survey_same_project",
        ),
        # RESTRICT is intentional: do not silently turn an assigned link into a
        # general reusable link.
        ForeignKeyConstraint(
            ["project_id", "assigned_subject_id"],
            ["project_subjects.project_id", "project_subjects.id"],
            ondelete="RESTRICT",
            name="fk_survey_links_assigned_subject_same_project",
        ),
    )

    @property
    def is_single_use(self) -> bool:
        """Single-use is derived from being assigned to an email or subject."""
        return self.assigned_email is not None or self.assigned_subject_id is not None

    survey: Mapped[Survey] = relationship("Survey", foreign_keys=[project_id, survey_id], overlaps="project")
    project: Mapped[Project] = relationship("Project", foreign_keys=[project_id], overlaps="survey")
    assigned_subject: Mapped[ProjectSubject | None] = relationship(
        "ProjectSubject",
        foreign_keys=[project_id, assigned_subject_id],
        overlaps="project,survey",
    )


SurveyPublicLink = SurveyLink
