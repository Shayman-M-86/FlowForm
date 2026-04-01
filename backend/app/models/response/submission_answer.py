from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ResponseBase

if TYPE_CHECKING:
    from app.models.response.submission import Submission


class SubmissionAnswer(ResponseBase):
    """A single answer to one question within a submission."""

    __tablename__ = "submission_answers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False
    )
    question_key: Mapped[str] = mapped_column(Text, nullable=False)
    answer_family: Mapped[str] = mapped_column(Text, nullable=False)
    answer_value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (UniqueConstraint("submission_id", "question_key", name="uq_submission_answers_question"),)

    submission: Mapped[Submission] = relationship("Submission", back_populates="answers")
