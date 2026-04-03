from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    # pk_<table>
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    # uq_<table>_<column>
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    # ix_<table>_<column>
    "fk": "fk_%(table_name)s_%(column_0_name)s__%(referred_table_name)s",
    # fk_<table>_<local_column>__<referred_table>
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    # ck_<table>_<explicit_constraint_name>
}


class CoreBase(DeclarativeBase):
    """Application declarative base class for SQLAlchemy ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class ResponseBase(DeclarativeBase):
    """Application declarative base class for SQLAlchemy ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
