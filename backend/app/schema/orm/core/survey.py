from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CoreBase
from app.schema.enums import SurveyVersionStatus, SurveyVisibility
from app.schema.models.common.types import Slug, Timestamp
from app.schema.models.identity.types import UserId
from app.schema.models.projects.types import ProjectId
from app.schema.models.response_store.types import ResponseStoreId
from app.schema.models.survey.types import SurveyId, SurveyTitle, SurveyVersionId, SurveyVersionNumber
from app.schema.orm.base import TimestampMixin

if TYPE_CHECKING:
    from app.schema.orm.core.user import User


class Survey(TimestampMixin, CoreBase, kw_only=True):
    """A survey definition belonging to a project."""

    __tablename__ = "surveys"

    id: Mapped[SurveyId] = mapped_column(BigInteger, Identity(), primary_key=True, init=False)
    project_id: Mapped[ProjectId] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[SurveyTitle] = mapped_column(Text, nullable=False)
    visibility: Mapped[SurveyVisibility] = mapped_column(Text, default="private", nullable=False)
    public_slug: Mapped[Slug | None] = mapped_column(Text, unique=True, nullable=True, default=None)
    default_response_store_id: Mapped[ResponseStoreId | None] = mapped_column(BigInteger, nullable=True, default=None)
    published_version_id: Mapped[SurveyVersionId | None] = mapped_column(BigInteger, nullable=True, default=None)
    created_by_user_id: Mapped[UserId | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, default=None
    )

    # Only necessary constraints live in SQLAlchemy; source of truth is the SQL schema file.
    __table_args__ = (
        UniqueConstraint("project_id", "id", name="uq_surveys_project_id_id"),
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
        init=False,
    )

    # The currently active published version — post_update defers the UPDATE
    # until after both Survey and SurveyVersion INSERTs are flushed, breaking
    # the insert-order cycle. Remove if integration tests show it's unnecessary.
    published_version: Mapped[SurveyVersion | None] = relationship(
        "SurveyVersion",
        primaryjoin="Survey.published_version_id == SurveyVersion.id",
        foreign_keys="[Survey.published_version_id]",
        post_update=True,
        init=False,
    )

    created_by: Mapped[User | None] = relationship("User", foreign_keys="[Survey.created_by_user_id]", init=False)


class SurveyVersion(TimestampMixin, CoreBase, kw_only=True):
    """A versioned survey document."""

    __tablename__ = "survey_versions"

    id: Mapped[SurveyVersionId] = mapped_column(BigInteger, Identity(), primary_key=True, init=False)
    survey_id: Mapped[SurveyId] = mapped_column(
        BigInteger, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[SurveyVersionNumber] = mapped_column(Integer, nullable=False)
    status: Mapped[SurveyVersionStatus] = mapped_column(Text, default="draft", nullable=False)
    definition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    published_at: Mapped[Timestamp | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    created_by_user_id: Mapped[UserId | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, default=None
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)

    # Only necessary constraints live in SQLAlchemy; source of truth is the SQL schema file.
    __table_args__ = (UniqueConstraint("survey_id", "id", name="uq_survey_versions_survey_id_id"),)

    survey: Mapped[Survey] = relationship(
        "Survey",
        primaryjoin="SurveyVersion.survey_id == Survey.id",
        foreign_keys="[SurveyVersion.survey_id]",
        back_populates="versions",
        init=False,
    )

    created_by: Mapped[User | None] = relationship(
        "User", foreign_keys="[SurveyVersion.created_by_user_id]", init=False
    )
