import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ResponseBase

if TYPE_CHECKING:
    from app.models.response.submission_answer import SubmissionAnswer
    from app.models.response.submission_event import SubmissionEvent


class Submission(ResponseBase):
    """Raw submission payload stored in the isolated response database."""

    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    core_submission_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    survey_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    survey_version_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    pseudonymous_subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    submission_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    answers: Mapped[list[SubmissionAnswer]] = relationship(
        "SubmissionAnswer", back_populates="submission", cascade="all, delete-orphan"
    )
    events: Mapped[list[SubmissionEvent]] = relationship(
        "SubmissionEvent", back_populates="submission", cascade="all, delete-orphan"
    )
