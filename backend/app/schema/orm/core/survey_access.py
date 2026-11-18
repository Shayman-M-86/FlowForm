from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Table,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CoreBase
from app.schema.enums import SurveyLinkAssignmentSource, SurveyLinkType
from app.schema.models.common.types import Timestamp
from app.schema.models.projects.types import ParticipantId, ProjectId, ProjectMembershipId, RoleDescription, RoleName
from app.schema.models.survey.types import SurveyAccessLinkName, SurveyAccessToken, SurveyId, SurveyLinkId, SurveyRoleId

if TYPE_CHECKING:
    from app.schema.orm.core.permission import Permission
    from app.schema.orm.core.project import Project, ProjectMembership
    from app.schema.orm.core.project_participant import ProjectParticipant
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


class SurveyRole(CoreBase, kw_only=True):
    """A survey-level role override scoped to a project."""

    __tablename__ = "survey_roles"

    id: Mapped[SurveyRoleId] = mapped_column(BigInteger, primary_key=True, init=False)
    project_id: Mapped[ProjectId] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[RoleName] = mapped_column(Text, nullable=False)
    description: Mapped[RoleDescription | None] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[Timestamp] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, init=False
    )

    # Only necessary constraints live in SQLAlchemy; source of truth is the SQL schema file.
    __table_args__ = (UniqueConstraint("project_id", "id", name="uq_survey_roles_project_id_id"),)

    permissions: Mapped[list[Permission]] = relationship("Permission", secondary=survey_role_permissions, init=False)

    membership_roles: Mapped[list[SurveyMembershipRole]] = relationship(
        "SurveyMembershipRole", back_populates="role", overlaps="survey,membership", init=False
    )


class SurveyMembershipRole(CoreBase, kw_only=True):
    """Assigns a survey-level role to a project membership for a specific survey."""

    __tablename__ = "survey_membership_roles"

    project_id: Mapped[ProjectId] = mapped_column(BigInteger, nullable=False)
    survey_id: Mapped[SurveyId] = mapped_column(BigInteger, primary_key=True)
    membership_id: Mapped[ProjectMembershipId] = mapped_column(BigInteger, primary_key=True)
    role_id: Mapped[SurveyRoleId] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[Timestamp] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, init=False
    )

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
        "Survey", overlaps="membership,role,membership_roles,survey_roles", init=False
    )

    membership: Mapped[ProjectMembership] = relationship(
        "ProjectMembership", back_populates="survey_roles", overlaps="survey,role,membership_roles", init=False
    )

    role: Mapped[SurveyRole] = relationship(
        "SurveyRole", back_populates="membership_roles", overlaps="survey,membership,survey_roles", init=False
    )


class SurveyLink(CoreBase, kw_only=True):
    """Bearer-token link granting survey access.

    project_id is stored directly so the database can prove the link, its survey,
    and its assigned participant all belong to the same project. A link's assigned
    subject and email are not stored here — they are reached by joining through
    the assigned participant.
    """

    __tablename__ = "survey_links"

    id: Mapped[SurveyLinkId] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), init=False
    )
    project_id: Mapped[ProjectId] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    survey_id: Mapped[SurveyId] = mapped_column(BigInteger, nullable=False)
    name: Mapped[SurveyAccessLinkName] = mapped_column(Text, nullable=False)
    token: Mapped[SurveyAccessToken] = mapped_column(Text, nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False, default=True)
    link_type: Mapped[SurveyLinkType] = mapped_column(
        Text, server_default=text("'general'"), nullable=False, default="general"
    )
    # How the assignment was created ('manual' | 'automated'). Informational only.
    assignment_source: Mapped[SurveyLinkAssignmentSource] = mapped_column(Text, nullable=False)
    # The sole assignment. A participant resolves to a subject AND an identity,
    # so the link reaches both through this column alone.
    assigned_participant_id: Mapped[ParticipantId | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, default=None
    )
    expires_at: Mapped[Timestamp | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    used_at: Mapped[Timestamp | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    emailed_at: Mapped[Timestamp | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    created_at: Mapped[Timestamp] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, init=False
    )

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
            ["project_id", "assigned_participant_id"],
            ["project_participants.project_id", "project_participants.id"],
            ondelete="RESTRICT",
            name="fk_survey_links_assigned_participant_same_project",
        ),
    )

    @property
    def is_single_use(self) -> bool:
        """Single-use is derived from carrying a participant assignment."""
        return self.assigned_participant_id is not None

    survey: Mapped[Survey] = relationship(
        "Survey", foreign_keys=[project_id, survey_id], overlaps="project", init=False
    )
    project: Mapped[Project] = relationship("Project", foreign_keys=[project_id], overlaps="survey", init=False)
    assigned_participant: Mapped[ProjectParticipant | None] = relationship(
        "ProjectParticipant", foreign_keys=[project_id, assigned_participant_id], overlaps="project,survey", init=False
    )
