from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CoreBase
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.core.project import Project
    from app.models.core.user import User


class ResponseStore(TimestampMixin, CoreBase):
    """Defines a destination for survey response payloads."""

    __tablename__ = "response_stores"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    store_type: Mapped[str] = mapped_column(Text, nullable=False)
    connection_reference: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("project_id", "id", name="uq_response_stores_project_id_id"),
        UniqueConstraint("project_id", "name", name="uq_response_stores_project_id_name"),
        CheckConstraint("store_type IN ('platform_postgres', 'external_postgres')", name="store_type_valid"),
        CheckConstraint("jsonb_typeof(connection_reference) = 'object'", name="connection_reference_is_object"),
    )

    project: Mapped[Project] = relationship("Project", foreign_keys=[project_id])
    created_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[created_by_user_id]
    )
