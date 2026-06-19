import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, SmallInteger, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import CoreBase


class LinkageKeyVersion(CoreBase):
    """Lookup table mapping app-level linkage key versions to AWS Secrets Manager version IDs."""

    __tablename__ = "linkage_key_versions"

    version: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    aws_secret_id: Mapped[str] = mapped_column(Text, nullable=False)
    aws_secret_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("aws_secret_id", "aws_secret_version_id", name="uq_linkage_key_versions_aws_secret_version"),
    )
