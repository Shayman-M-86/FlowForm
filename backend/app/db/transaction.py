import contextlib

from sqlalchemy.orm import Session


def commit_or_rollback(db: Session) -> None:
    """Attempt to commit the session, rolling back if an exception occurs."""
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

def rollback_safely(*sessions: Session) -> None:
    """Attempt to roll back multiple sessions, suppressing any exceptions that occur during rollback."""
    for session in sessions:
        with contextlib.suppress(Exception):
            session.rollback()
