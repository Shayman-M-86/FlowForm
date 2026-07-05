import re

from sqlalchemy.orm import Session

from app.core.extensions import auth
from app.db.transaction import commit_or_rollback
from app.domain import auth_rules
from app.repositories import projects_repo as pr
from app.repositories import users_repo as ur
from app.schema.api.requests.auth import BootstrapUserRequest
from app.schema.api.requests.projects import CreateProjectRequest
from app.services.results import BootstrapCurrentUserResult
from app.services.users import UserService

_SLUG_INVALID_CHARS_RE = re.compile(r"[^a-z0-9-]+")


def _default_project_slug(public_id: str, *, user_id: int) -> str:
    """Build a slug-safe default project slug from a user public_id."""
    slug = public_id.lower().replace("_", "-")
    slug = _SLUG_INVALID_CHARS_RE.sub("-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        slug = f"user-{user_id}"
    return slug

class AuthService:
    """Service for authenticated user bootstrap flows."""

    def __init__(self, user_service: UserService | None = None) -> None:
        self.user_service = user_service or UserService()

    def bootstrap_current_user(
        self,
        db: Session,
        *,
        access_token_sub: str,
        payload: BootstrapUserRequest,
    ) -> BootstrapCurrentUserResult:
        """Verify the ID token and create or update the local user."""
        user = ur.get_user_by_auth0_user_id(db, access_token_sub)
        if user:
            return BootstrapCurrentUserResult(user=user, created=False)

        id_token_claims = auth.verify_id_token(payload.id_token)
        id_token_sub = auth_rules.ensure_subject(claims=id_token_claims)
        auth_rules.ensure_subject_matches(
            access_token_sub=access_token_sub,
            id_token_sub=id_token_sub,
        )
        email = auth_rules.ensure_email(claims=id_token_claims)
        display_name = auth_rules.normalize_display_name(claims=id_token_claims)
        email_verified = auth_rules.extract_email_verified(claims=id_token_claims)
        user, created = self.user_service.bootstrap_user(
            db,
            auth0_user_id=id_token_sub,
            email=email,
            display_name=display_name,
            email_verified=email_verified,
        )

        default_project = None
        if created:
            default_project = pr.create_project(
                db,
                CreateProjectRequest(
                    name="My Project",
                    slug=_default_project_slug(user.public_id, user_id=user.id),
                ),
                created_by_user_id=user.id,
            )
            commit_or_rollback(db)

        return BootstrapCurrentUserResult(user=user, created=created, default_project=default_project)
