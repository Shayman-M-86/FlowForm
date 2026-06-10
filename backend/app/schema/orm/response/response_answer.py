import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, LargeBinary, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ResponseBase

if TYPE_CHECKING:
    from app.schema.orm.response.response_answer_revision import ResponseAnswerRevision
    from app.schema.orm.response.response_envelope import ResponseEnvelope


class ResponseAnswer(ResponseBase):
    """Stable logical answer row for one encrypted question answer."""

    __tablename__ = "response_answers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    envelope_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("response_envelopes.id", ondelete="CASCADE"), nullable=False
    )
    answer_locator: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    latest_revision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    __table_args__ = (
        CheckConstraint("octet_length(answer_locator) = 32", name="answer_locator_len"),
        UniqueConstraint("id", "envelope_id", name="uq_response_answers_id_envelope_id"),
        UniqueConstraint("envelope_id", "answer_locator", name="uq_response_answers_envelope_id_answer_locator"),
        ForeignKeyConstraint(
            ["latest_revision_id", "id"],
            ["response_answer_revisions.id", "response_answer_revisions.answer_id"],
            name="fk_response_answers_latest_revision_same_answer",
            deferrable=True,
            initially="DEFERRED",
            use_alter=True,
        ),
    )

    envelope: Mapped[ResponseEnvelope] = relationship(
        "ResponseEnvelope",
        back_populates="answers",
        foreign_keys=[envelope_id],
    )
    revisions: Mapped[list[ResponseAnswerRevision]] = relationship(
        "ResponseAnswerRevision",
        back_populates="answer",
        cascade="all, delete-orphan",
        foreign_keys="[ResponseAnswerRevision.answer_id]",
    )
    latest_revision: Mapped[ResponseAnswerRevision] = relationship(
        "ResponseAnswerRevision",
        foreign_keys=[latest_revision_id],
        post_update=True,
    )
