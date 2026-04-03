from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ResponseBase

if TYPE_CHECKING:
    from app.schema.orm.response.submission import Submission


class SubmissionEvent(ResponseBase):
    """An event record for async delivery tracking on a submission."""

    __tablename__ = "submission_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    event_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "event_payload IS NULL OR jsonb_typeof(event_payload) = 'object'", name="event_payload_is_object"
        ),
    )

    submission: Mapped[Submission] = relationship("Submission", back_populates="events")
