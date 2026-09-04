import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKeyConstraint, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CoreBase

if TYPE_CHECKING:
    from app.schema.orm.core.submission_session import SubmissionSession


class SubmissionAnswerSlot(CoreBase):
    """Stable core-side pointer for one submission session/field answer."""

    __tablename__ = "submission_answer_slots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    submission_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    survey_version_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    field_id: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "submission_session_id",
            "field_id",
            name="uq_submission_answer_slots_session_field",
        ),
        ForeignKeyConstraint(
            ["submission_session_id", "survey_version_id"],
            ["submission_sessions.id", "submission_sessions.survey_version_id"],
            ondelete="CASCADE",
            name="fk_submission_answer_slots_session_version",
        ),
    )

    session: Mapped[SubmissionSession] = relationship(
        "SubmissionSession", foreign_keys=[submission_session_id]
    )
