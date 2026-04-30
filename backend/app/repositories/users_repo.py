from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
from app.schema.orm.core.user import User

_PUBLIC_ID_CONSTRAINT = "uq_users_public_id"
_MAX_PUBLIC_ID_RETRIES = 5


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
    for attempt in range(_MAX_PUBLIC_ID_RETRIES):
        user = User(
            auth0_user_id=auth0_user_id,
            email=email,
            display_name=display_name,
        )
        db.add(user)
        try:
            flush_with_err_handle(db)
            return user
        except IntegrityError as exc:
            constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", "") or ""
            is_public_id_collision = (
                isinstance(exc.orig, UniqueViolation)
                and constraint == _PUBLIC_ID_CONSTRAINT
                and attempt < _MAX_PUBLIC_ID_RETRIES - 1
            )
            if is_public_id_collision:
                continue
            raise

    raise RuntimeError("Failed to generate a unique public_id after retries")


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
