

from sqlalchemy.orm import DeclarativeBase

from app.db.naming import metadata_obj


class CoreBase(DeclarativeBase):
    """Application declarative base class for SQLAlchemy ORM models."""

    metadata = metadata_obj

class ResponseBase(DeclarativeBase):
    """Application declarative base class for SQLAlchemy ORM models."""

    metadata = metadata_obj