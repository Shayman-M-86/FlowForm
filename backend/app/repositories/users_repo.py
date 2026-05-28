from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.schema.orm.core.user import User

_PUBLIC_ID_CONSTRAINT = "uq_users_public_id"
_MAX_PUBLIC_ID_RETRIES = 5


def get_user_by_email(db: Session, email: str) -> User | None:
    """Return the user row for a given email address, if it exists."""
    return db.scalar(select(User).where(User.email == email))


def get_user_by_auth0_user_id(db: Session, auth0_user_id: str) -> User | None:
    """Return the user row for an Auth0 subject, if it exists."""
    return db.scalar(select(User).where(User.auth0_user_id == auth0_user_id))


def create_user(
    db: Session,
    *,
    auth0_user_id: str,
    email: str,
    display_name: str | None,
) -> User:
    """Create and flush a new user row, retrying on public_id collisions."""
    attempt = 0
    while True:
        attempt += 1
        user = User(
            auth0_user_id=auth0_user_id,
            email=email,
            display_name=display_name,
        )
        db.add(user)
        try:
            db.flush()
            return user
        except IntegrityError as exc:
            db.rollback()
            constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", "") or ""
            is_public_id_collision = (
                isinstance(exc.orig, UniqueViolation)
                and constraint == _PUBLIC_ID_CONSTRAINT
                and attempt < _MAX_PUBLIC_ID_RETRIES
            )
            if is_public_id_collision:
                continue
            raise


def update_user(
    user: User,
    *,
    email: str,
    display_name: str | None,
) -> User:
    """Update the mutable identity fields for a user row."""
    user.email = email
    user.display_name = display_name
    return user


def update_user_email(user: User, *, email: str) -> User:
    """Update only the email field on a user row."""
    user.email = email
    return user


def delete_user(db: Session, user: User) -> None:
    """Mark a user row for deletion (flushed on the next commit)."""
    db.delete(user)
