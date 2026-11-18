from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import CoreBase


class Permission(CoreBase, kw_only=True):
    """A named permission that can be assigned to project or survey roles."""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
