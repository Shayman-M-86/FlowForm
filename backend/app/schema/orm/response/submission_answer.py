from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ResponseBase

if TYPE_CHECKING:
    from app.schema.orm.response.submission import Submission


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

    __table_args__ = (
        UniqueConstraint(
            "submission_id",
            "question_key",
            name="uq_submission_answers_question",
        ),
        CheckConstraint(
            "answer_family IN ('choice', 'field', 'matching', 'rating')",
            name="ck_submission_answers_answer_family_valid",
        ),
        CheckConstraint(
            "jsonb_typeof(answer_value) = 'object'",
            name="ck_submission_answers_answer_value_is_object",
        ),
        CheckConstraint(
            "answer_family <> 'choice'"
            " OR (jsonb_has_exact_keys(answer_value, ARRAY['selected'])"
            " AND jsonb_array_is_text_array(answer_value->'selected'))",
            name="ck_submission_answers_choice_shape_valid",
        ),
        CheckConstraint(
            "answer_family <> 'field'"
            " OR (jsonb_has_exact_keys(answer_value, ARRAY['value'])"
            " AND jsonb_is_scalar_or_null(answer_value->'value'))",
            name="ck_submission_answers_field_shape_valid",
        ),
        CheckConstraint(
            "answer_family <> 'matching'"
            " OR (jsonb_has_exact_keys(answer_value, ARRAY['matches'])"
            " AND jsonb_matching_matches_valid(answer_value->'matches'))",
            name="ck_submission_answers_matching_shape_valid",
        ),
        CheckConstraint(
            "answer_family <> 'rating'"
            " OR (jsonb_has_exact_keys(answer_value, ARRAY['value'])"
            " AND jsonb_typeof(answer_value->'value') = 'number')",
            name="ck_submission_answers_rating_shape_valid",
        ),
    )
    submission: Mapped[Submission] = relationship("Submission", back_populates="answers")
