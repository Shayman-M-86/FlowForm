import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    LargeBinary,
    SmallInteger,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import CoreBase


class SurveyEncryptionKey(CoreBase):
    """KMS-wrapped survey branch key used to wrap session DEKs."""

    __tablename__ = "survey_encryption_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    project_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    survey_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    wrapped_survey_branch_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    kms_key_arn: Mapped[str] = mapped_column(Text, nullable=False)
    kms_context_version: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("survey_id", name="uq_survey_encryption_keys_survey"),
        UniqueConstraint("project_id", "survey_id", name="uq_survey_encryption_keys_project_survey"),
        ForeignKeyConstraint(
            ["project_id", "survey_id"],
            ["surveys.project_id", "surveys.id"],
            ondelete="CASCADE",
            name="fk_survey_encryption_keys_survey_same_project",
        ),
        CheckConstraint("octet_length(wrapped_survey_branch_key) > 0", name="wrapped_key_len"),
        CheckConstraint("char_length(btrim(kms_key_arn)) BETWEEN 1 AND 2048", name="kms_key_arn_len"),
        CheckConstraint("kms_context_version > 0", name="kms_context_version_valid"),
        Index("ix_survey_encryption_keys_project_survey", "project_id", "survey_id"),
    )
