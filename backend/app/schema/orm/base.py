from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from app.schema.types import Timestamp


class TimestampMixin(MappedAsDataclass, kw_only=True, eq=False, repr=False):
    """Mixin that adds ``created_at`` and ``updated_at`` timestamp columns.

    ``updated_at`` is maintained by a database-level trigger (``set_updated_at``),
    so it is not set via ``onupdate`` here.
    """

    created_at: Mapped[Timestamp] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), init=False
    )
    updated_at: Mapped[Timestamp] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), init=False
    )


def utc_now() -> Timestamp:
    """Creation-time default; persisted timestamps still come from stored values."""
    return datetime.now(UTC)
