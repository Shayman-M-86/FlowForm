from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CoreBase
from app.schema.orm.base import TimestampMixin

if TYPE_CHECKING:
    from app.schema.orm.core.user import User


class Survey(TimestampMixin, CoreBase):
    """A survey definition belonging to a project."""

    __tablename__ = "surveys"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(Text, default="private", nullable=False)
    public_slug: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    default_response_store_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    published_version_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("project_id", "id", name="uq_surveys_project_id_id"),
        CheckConstraint("visibility IN ('private', 'link_only', 'public')", name="visibility_valid"),
        CheckConstraint("visibility <> 'public' OR public_slug IS NOT NULL", name="public_requires_slug"),
        CheckConstraint(
            "public_slug IS NULL OR visibility = 'public'",
            name="slug_requires_public_visibility",
        ),
        ForeignKeyConstraint(
            ["default_response_store_id"],
            ["response_stores.id"],
            ondelete="SET NULL",
            name="fk_surveys_default_store",
        ),
        ForeignKeyConstraint(
            ["project_id", "default_response_store_id"],
            ["response_stores.project_id", "response_stores.id"],
            name="fk_surveys_default_store_same_project",
        ),
        # Deferred — survey_versions table doesn't exist yet at Survey DDL time
        ForeignKeyConstraint(
            ["id", "published_version_id"],
            ["survey_versions.survey_id", "survey_versions.id"],
            ondelete="SET NULL",
            name="fk_surveys_published_version_same_survey",
            use_alter=True,
        ),
    )

    # All versions of this survey
    versions: Mapped[list[SurveyVersion]] = relationship(
        "SurveyVersion",
        primaryjoin="Survey.id == SurveyVersion.survey_id",
        foreign_keys="[SurveyVersion.survey_id]",
        back_populates="survey",
        passive_deletes=True,
    )

    # The currently active published version — post_update defers the UPDATE
    # until after both Survey and SurveyVersion INSERTs are flushed, breaking
    # the insert-order cycle. Remove if integration tests show it's unnecessary.
    published_version: Mapped[SurveyVersion | None] = relationship(
        "SurveyVersion",
        primaryjoin="Survey.published_version_id == SurveyVersion.id",
        foreign_keys="[Survey.published_version_id]",
        post_update=True,
    )

    created_by: Mapped[User | None] = relationship("User", foreign_keys="[Survey.created_by_user_id]")


class SurveyVersion(TimestampMixin, CoreBase):
    """A versioned snapshot of a survey's questions and rules."""

    __tablename__ = "survey_versions"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    survey_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="draft", nullable=False)
    compiled_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("survey_id", "id", name="uq_survey_versions_survey_id_id"),
        UniqueConstraint("survey_id", "version_number", name="uq_survey_versions_survey_id_version_number"),
        CheckConstraint("status IN ('draft', 'published', 'archived')", name="status_valid"),
        CheckConstraint("version_number > 0", name="version_number_positive"),
        CheckConstraint(
            "status <> 'published' OR (compiled_schema IS NOT NULL AND published_at IS NOT NULL)",
            name="published_requires_schema_and_timestamp",
        ),
        Index(
            "uq_survey_versions_one_published",
            "survey_id",
            unique=True,
            postgresql_where=text("status = 'published' AND deleted_at IS NULL"),
        ),
    )

    survey: Mapped[Survey] = relationship(
        "Survey",
        primaryjoin="SurveyVersion.survey_id == Survey.id",
        foreign_keys="[SurveyVersion.survey_id]",
        back_populates="versions",
    )

    created_by: Mapped[User | None] = relationship("User", foreign_keys="[SurveyVersion.created_by_user_id]")
