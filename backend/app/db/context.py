from flask import g
from sqlalchemy.orm import Session


def get_core_db() -> Session:
    """Get the core database session from the Flask `g` context."""
    db = getattr(g, "core_db", None)
    if db is None:
        raise RuntimeError("Core database session is not available.")
    return db


def get_response_db() -> Session:
    """Get the response database session from the Flask `g` context."""
    db = getattr(g, "response_db", None)
    if db is None:
        raise RuntimeError("Response database session is not available.")
    return db
