from logging import getLogger

from flask import Flask, g
from sqlalchemy.orm import Session

from app.core.extensions import db_manager

logger = getLogger(__name__)


def open_request_sessions() -> None:
    """Open database sessions for the current request."""
    g.core_db = db_manager.create_core_session()
    g.response_db = db_manager.create_response_session()


def close_request_sessions(exc: BaseException | None) -> None:
    """Close database sessions after each request, rolling back if an exception occurred."""
    for key in ("core_db", "response_db"):
        db: Session | None = g.pop(key, None)
        if db is None:
            continue

        try:
            if exc:
                db.rollback()
        finally:
            db.close()


def init_db_sessions(app: Flask) -> None:
    """Initialize database sessions for each request."""
    logger.debug("Initializing database sessions for each request")
    app.before_request(open_request_sessions)
    logger.debug("Registering teardown_request to close database sessions")
    app.teardown_request(close_request_sessions)
