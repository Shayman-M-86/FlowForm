from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.transaction import commit_or_rollback
from app.domain import user_rules
from app.domain.errors import UserBootstrapConflictError
from app.repositories import users_repo
from app.schema.orm.core.user import User


class UserService:
    """Bootstrap and synchronize authenticated users."""

    def bootstrap_user(
        self,
        db: Session,
        *,
        auth0_user_id: str,
        email: str,
        display_name: str | None,
    ) -> tuple[User, bool]:
        """Create or update a user row for the authenticated Auth0 subject."""
        existing = users_repo.get_user_by_auth0_user_id(db, auth0_user_id)
        created = existing is None

        try:
            if existing is None:
                user = users_repo.create_user(
                    db,
                    auth0_user_id=auth0_user_id,
                    email=email,
                    display_name=display_name,
                )
            else:
                user = users_repo.update_user(
                    existing,
                    email=email,
                    display_name=display_name,
                )

            commit_or_rollback(db)
        except IntegrityError as exc:
            constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", "") or ""

            if isinstance(exc.orig, UniqueViolation) and "auth0_user_id" in constraint:
                user = user_rules.ensure_user_exists(
                    auth0_user_id=auth0_user_id, user=users_repo.get_user_by_auth0_user_id(db, auth0_user_id)
                )
                users_repo.update_user(user, email=email, display_name=display_name)
                commit_or_rollback(db)
                return user, False

            if isinstance(exc.orig, UniqueViolation) and "email" in constraint:
                raise UserBootstrapConflictError(email=email) from None

            raise

        return user, created

    def get_user_by_sub(self, db: Session, auth0_user_id: str) -> User:
        """Get a user by their Auth0 user ID."""
        user = user_rules.ensure_user_exists(
            auth0_user_id=auth0_user_id, user=users_repo.get_user_by_auth0_user_id(db, auth0_user_id)
        )
        return user
