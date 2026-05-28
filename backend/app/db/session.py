from logging import getLogger

from flask import Flask, g
from sqlalchemy.orm import Session

from app.core.extensions import db_manager

logger = getLogger(__name__)


def open_request_sessions() -> None:
    """Create per-request sessions for the core and response databases and store them on Flask's g."""
    g.core_db = db_manager.create_core_session()
    g.response_db = db_manager.create_response_session()


def close_request_sessions(exc: BaseException | None) -> None:
    """Tear down per-request database sessions after each request.

    If the request raised an exception, both sessions are rolled back before closing
    so that no partial writes are left open. Sessions that were never created are skipped.
    """
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
    """Register request lifecycle hooks that manage database session setup and teardown.

    Attaches open_request_sessions as a before_request hook and
    close_request_sessions as a teardown_request hook on the given Flask app.
    """
    logger.debug("Initializing database sessions for each request")
    app.before_request(open_request_sessions)
    logger.debug("Registering teardown_request to close database sessions")
    app.teardown_request(close_request_sessions)
