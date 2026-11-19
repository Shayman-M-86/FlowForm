from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import CoreBase
from app.schema.types import PermissionName


class Permission(CoreBase, kw_only=True):
    """A named permission that can be assigned to project or survey roles."""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[PermissionName] = mapped_column(String, unique=True, nullable=False)
