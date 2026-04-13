from sqlalchemy.orm import Session

from app.core.extensions import auth
from app.domain import auth_rules
from app.schema.api.requests.auth import BootstrapUserRequest
from app.services.results import BootstrapCurrentUserResult
from app.services.users import UserService
from app.repositories import users_repo


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
        user = users_repo.get_user_by_auth0_user_id(db, access_token_sub)
        if user is not None:
            return BootstrapCurrentUserResult(user=user, created=False)
        
        id_token_claims = auth.verify_id_token(payload.id_token)
        id_token_sub = auth_rules.ensure_subject(claims=id_token_claims)
        auth_rules.ensure_subject_matches(
            access_token_sub=access_token_sub,
            id_token_sub=id_token_sub,
        )
        email = auth_rules.ensure_email(claims=id_token_claims)
        display_name = auth_rules.normalize_display_name(claims=id_token_claims)
        user, created = self.user_service.bootstrap_user(
            db,
            auth0_user_id=id_token_sub,
            email=email,
            display_name=display_name,
        )
        return BootstrapCurrentUserResult(user=user, created=created)
    
