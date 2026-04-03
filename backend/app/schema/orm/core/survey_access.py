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
    from app.schema.orm.core.permission import Permission
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("project_id", "id", name="uq_survey_roles_project_id_id"),
        UniqueConstraint("project_id", "name", name="uq_survey_roles_project_id_name"),
    )

    permissions: Mapped[list[Permission]] = relationship("Permission", secondary=survey_role_permissions)


class SurveyMembershipRole(CoreBase):
    """Assigns a survey-level role to a project membership for a specific survey."""

    __tablename__ = "survey_membership_roles"

    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    survey_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    membership_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(["project_id", "survey_id"],
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


class SurveyPublicLink(CoreBase):
    """A bearer-token link granting public access to a survey."""
    __tablename__ = "survey_public_links"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    survey_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False)
    token_prefix: Mapped[str] = mapped_column(Text, nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    allow_response: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_survey_public_links_token_hash"),
        UniqueConstraint("survey_id", "id", name="uq_survey_public_links_survey_id_id"),
        UniqueConstraint("survey_id", "token_prefix", name="uq_survey_public_links_survey_id_token_prefix"),
        CheckConstraint("char_length(token_prefix) BETWEEN 8 AND 32", name="ck_survey_public_links_token_prefix_len"),
        CheckConstraint("char_length(token_hash) >= 32", name="ck_survey_public_links_token_hash_len"),
    )

    survey: Mapped[Survey] = relationship("Survey")
