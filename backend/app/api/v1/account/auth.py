from flask import request

from app.api.utils.validation import parse
from app.api.v1.account import account_bp
from app.core.extensions import auth
from app.db.context import get_core_db
from app.openapi import openapi_route
from app.schema.api.requests.auth import BootstrapUserRequest
from app.schema.api.responses.auth import BootstrapUserResponses, CurrentUserResponses
from app.schema.api.responses.projects import ProjectResponses
from app.services.auth import AuthService

auth_service = AuthService()


@openapi_route(
    summary="Bootstrap current user",
    request_model=BootstrapUserRequest,
    response_model=BootstrapUserResponses,
    status_code=201,
    tags=["Auth"],
)
@account_bp.route("/bootstrap-user", methods=["POST"])
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

    response = BootstrapUserResponses(
        created=result.created,
        user=CurrentUserResponses.model_validate(result.user),
        default_project=ProjectResponses.model_validate(result.default_project) if result.default_project else None,
    )
    return response.model_dump(mode="json"), 201 if result.created else 200
