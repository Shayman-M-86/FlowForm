import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Integer, LargeBinary, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ResponseBase

if TYPE_CHECKING:
    from app.schema.orm.response.response_answer import ResponseAnswer


class ResponseAnswerRevision(ResponseBase):
    """Immutable encrypted revision for one logical response answer."""

    __tablename__ = "response_answer_revisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    answer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    envelope_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    client_mutation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    __table_args__ = (
        CheckConstraint("revision_number > 0", name="revision_number_valid"),
        CheckConstraint("octet_length(ciphertext) >= 16", name="ciphertext_len"),
        CheckConstraint("octet_length(nonce) = 12", name="nonce_len"),
        ForeignKeyConstraint(
            ["answer_id", "envelope_id"],
            ["response_answers.id", "response_answers.envelope_id"],
            ondelete="CASCADE",
            name="fk_response_answer_revisions_answer_same_envelope",
        ),
        UniqueConstraint("id", "answer_id", name="uq_response_answer_revisions_id_answer_id"),
        UniqueConstraint(
            "answer_id",
            "revision_number",
            name="uq_response_answer_revisions_answer_id_revision_number",
        ),
        UniqueConstraint("envelope_id", "nonce", name="uq_response_answer_revisions_envelope_id_nonce"),
        UniqueConstraint(
            "answer_id",
            "client_mutation_id",
            name="uq_response_answer_revisions_answer_id_client_mutation_id",
        ),
    )

    answer: Mapped[ResponseAnswer] = relationship(
        "ResponseAnswer",
        back_populates="revisions",
        foreign_keys=[answer_id],
    )
