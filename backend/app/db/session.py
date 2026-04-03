from flask import g

from app.core.extensions import db_manager


def open_request_sessions() -> None:
    """Open database sessions for the current request."""
    g.core_db = db_manager.create_core_session()
    g.response_db = db_manager.create_response_session()


def close_request_sessions(exception: Exception | None = None) -> None:
    """Close database sessions after each request, rolling back if an exception occurred."""
    for key in ("core_db", "response_db"):
        db = g.pop(key, None)
        if db is None:
            continue

        try:
            if exception is not None:
                db.rollback()
        finally:
            db.close()


def init_db_sessions(app) -> None:
    """Initialize database sessions for each request."""
    app.before_request(open_request_sessions)
    app.teardown_request(close_request_sessions)

    app.teardown_request(close_request_sessions)
