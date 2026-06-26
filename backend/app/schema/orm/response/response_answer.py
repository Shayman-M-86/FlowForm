import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, LargeBinary, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ResponseBase

if TYPE_CHECKING:
    from app.schema.orm.response.response_envelope import ResponseEnvelope


class ResponseAnswer(ResponseBase):
    """Current encrypted answer row for one core-side answer slot."""

    __tablename__ = "response_answers"

    answer_locator: Mapped[bytes] = mapped_column(LargeBinary, primary_key=True)
    envelope_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("response_envelopes.id", ondelete="CASCADE"), nullable=False
    )
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    client_mutation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("octet_length(answer_locator) = 32", name="answer_locator_len"),
        CheckConstraint("octet_length(nonce) = 12", name="nonce_len"),
        CheckConstraint("octet_length(ciphertext) > 0", name="ciphertext_non_empty"),
        UniqueConstraint("envelope_id", "nonce", name="uq_response_answers_envelope_id_nonce"),
    )

    envelope: Mapped["ResponseEnvelope"] = relationship(
        "ResponseEnvelope",
        back_populates="answers",
        foreign_keys=[envelope_id],
    )
