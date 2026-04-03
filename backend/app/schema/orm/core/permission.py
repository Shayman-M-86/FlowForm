from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import CoreBase


class Permission(CoreBase):
    """A named permission that can be assigned to project or survey roles."""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
