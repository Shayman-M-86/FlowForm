import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, LargeBinary, SmallInteger, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ResponseBase

if TYPE_CHECKING:
    from app.schema.orm.response.response_answer import ResponseAnswer


class ResponseEnvelope(ResponseBase):
    """Anonymous encrypted response envelope for one survey session."""

    __tablename__ = "response_envelopes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    session_locator: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    linkage_key_version: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    wrapped_session_dek: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    crypto_version: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint("session_locator", name="uq_response_envelopes_session_locator"),
        CheckConstraint("octet_length(session_locator) = 32", name="session_locator_len"),
        CheckConstraint("linkage_key_version > 0", name="linkage_key_version_valid"),
        CheckConstraint("octet_length(wrapped_session_dek) > 0", name="wrapped_session_dek_len"),
        CheckConstraint("crypto_version > 0", name="crypto_version_valid"),
    )

    answers: Mapped[list[ResponseAnswer]] = relationship(
        "ResponseAnswer",
        back_populates="envelope",
        cascade="all, delete-orphan",
        foreign_keys="[ResponseAnswer.envelope_id]",
    )
