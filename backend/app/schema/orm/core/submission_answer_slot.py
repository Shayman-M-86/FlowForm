from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKeyConstraint, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CoreBase
from app.schema.models.submission.types import SubmissionSessionId
from app.schema.models.survey.types import ReadableId, SurveyFieldUuid, SurveyVersionId

if TYPE_CHECKING:
    from app.schema.orm.core.submission_session import SubmissionSession


ANSWER_SLOT_IDENTITY_CONSTRAINT = "uq_submission_answer_slots_session_field"


class SubmissionAnswerSlot(CoreBase, kw_only=True):
    """Stable core-side pointer for one submission session/field answer."""

    __tablename__ = "submission_answer_slots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(), init=False
    )
    submission_session_id: Mapped[SubmissionSessionId] = mapped_column(UUID(as_uuid=True), nullable=False)
    survey_version_id: Mapped[SurveyVersionId] = mapped_column(BigInteger, nullable=False)
    # Field membership is checked against the version document, not a node table.
    field_uuid: Mapped[SurveyFieldUuid] = mapped_column(UUID(as_uuid=True), nullable=False)
    field_id: Mapped[ReadableId | None] = mapped_column(Text, nullable=True, default=None)

    __table_args__ = (
        UniqueConstraint(
            "submission_session_id",
            "field_uuid",
            name=ANSWER_SLOT_IDENTITY_CONSTRAINT,
        ),
        ForeignKeyConstraint(
            ["submission_session_id", "survey_version_id"],
            ["submission_sessions.id", "submission_sessions.survey_version_id"],
            ondelete="CASCADE",
            name="fk_submission_answer_slots_session_version",
        ),
    )

    session: Mapped[SubmissionSession] = relationship(
        "SubmissionSession", foreign_keys=[submission_session_id], init=False
    )
