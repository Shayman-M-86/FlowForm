from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CoreBase
from app.schema.enums import ResponseStoreType
from app.schema.models.identity.types import UserId
from app.schema.models.projects.types import ProjectId
from app.schema.models.response_store.types import ResponseStoreId
from app.schema.orm.base import TimestampMixin

if TYPE_CHECKING:
    from app.schema.orm.core.project import Project
    from app.schema.orm.core.user import User


class ResponseStore(TimestampMixin, CoreBase, kw_only=True):
    """Defines a destination for survey response payloads."""

    __tablename__ = "response_stores"

    id: Mapped[ResponseStoreId] = mapped_column(BigInteger, primary_key=True, init=False)
    project_id: Mapped[ProjectId] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    store_type: Mapped[ResponseStoreType] = mapped_column(Text, nullable=False)
    connection_reference: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_user_id: Mapped[UserId | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, default=None
    )

    # Only necessary constraints live in SQLAlchemy; source of truth is the SQL schema file.
    __table_args__ = (UniqueConstraint("project_id", "id", name="uq_response_stores_project_id_id"),)

    project: Mapped[Project] = relationship("Project", foreign_keys=[project_id], init=False)
    created_by: Mapped[User | None] = relationship("User", foreign_keys=[created_by_user_id], init=False)
