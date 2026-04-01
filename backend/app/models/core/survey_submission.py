import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, ForeignKeyConstraint, Index, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CoreBase

if TYPE_CHECKING:
    from app.models.core.user import User


class SurveySubmission(CoreBase):
    """Registry entry for a survey submission — metadata only, no raw answers."""

    __tablename__ = "survey_submissions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    survey_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    survey_version_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    response_store_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    submission_channel: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    public_link_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    pseudonymous_subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    external_submission_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, default="pending", nullable=False)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_delivery_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "survey_id"],
            ["surveys.project_id", "surveys.id"],
            ondelete="CASCADE",
            name="fk_survey_submissions_survey_same_project",
        ),
        ForeignKeyConstraint(
            ["survey_id", "survey_version_id"],
            ["survey_versions.survey_id", "survey_versions.id"],
            ondelete="RESTRICT",
            name="fk_survey_submissions_version_same_survey",
        ),
        ForeignKeyConstraint(
            ["response_store_id"],
            ["response_stores.id"],
            ondelete="RESTRICT",
            name="fk_survey_submissions_store",
        ),
        ForeignKeyConstraint(
            ["project_id", "response_store_id"],
            ["response_stores.project_id", "response_stores.id"],
            name="fk_survey_submissions_store_same_project",
        ),
        ForeignKeyConstraint(
            ["public_link_id"],
            ["survey_public_links.id"],
            ondelete="SET NULL",
            name="fk_survey_submissions_public_link",
        ),
        ForeignKeyConstraint(
            ["survey_id", "public_link_id"],
            ["survey_public_links.survey_id", "survey_public_links.id"],
            name="fk_survey_submissions_public_link_same_survey",
        ),
        ForeignKeyConstraint(
            ["project_id", "pseudonymous_subject_id"],
            [
                "response_subject_mappings.project_id",
                "response_subject_mappings.pseudonymous_subject_id",
            ],
            ondelete="RESTRICT",
            name="fk_survey_submissions_subject_same_project",
        ),
        Index(
            "uq_survey_submissions_external_submission_id",
            "response_store_id",
            "external_submission_id",
            unique=True,
            postgresql_where=text("external_submission_id IS NOT NULL"),
        ),
    )

    submitted_by: Mapped[User | None] = relationship("User", foreign_keys=[submitted_by_user_id])
