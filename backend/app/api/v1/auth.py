from flask import Blueprint, request

from app.api.utils.validation import parse
from app.core.extensions import auth
from app.db.context import get_core_db
from app.schema.api.requests.auth import BootstrapUserRequest
from app.schema.api.responses.auth import BootstrapUserOut, CurrentUserOut
from app.schema.api.responses.projects import ProjectOut
from app.services.auth import AuthService

auth_bp = Blueprint("auth_v1", __name__)

auth_service = AuthService()


@auth_bp.route("/bootstrap-user", methods=["POST"])
@auth.require_auth()
def bootstrap_user():
    """Create or confirm the current authenticated user in the local database."""
    payload = parse(BootstrapUserRequest, request)
    access_token_sub = auth.get_current_user_sub()
    db = get_core_db()
    result = auth_service.bootstrap_current_user(
        db,
        access_token_sub=access_token_sub,
        payload=payload,
    )

    response = BootstrapUserOut(
        created=result.created,
        user=CurrentUserOut.model_validate(result.user),
        default_project=ProjectOut.model_validate(result.default_project) if result.default_project else None,
    )
    return response.model_dump(mode="json"), 201 if result.created else 200
