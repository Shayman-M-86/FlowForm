from sqlalchemy.orm import Mapped, mapped_column

from app.core.extensions import db


class Permission(db.Model):
    """A named permission that can be assigned to project or survey roles."""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
