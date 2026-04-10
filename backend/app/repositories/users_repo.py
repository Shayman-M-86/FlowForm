from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
from app.schema.orm.core.user import User


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
    """Create and flush a new user row."""
    user = User(
        auth0_user_id=auth0_user_id,
        email=email,
        display_name=display_name,
    )
    db.add(user)
    flush_with_err_handle(db)
    return user


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
