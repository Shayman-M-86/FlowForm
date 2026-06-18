from flask import request

from app.api.utils.validation import parse
from app.api.v1.account import _users_service, account_bp
from app.core.extensions import auth
from app.db.context import get_core_db
from app.openapi import openapi_route
from app.schema.api.requests.me import (
    ChangeEmailRequest,
    ChangeUsernameRequest,
    UpdateProfileRequest,
)
from app.schema.api.responses.auth import CurrentUserResponses
from app.schema.api.responses.me import CurrentUserProfileResponses, PasswordChangeTicketResponses
from app.schema.orm.core.user import User
from app.services.account import account_service


@openapi_route(
    summary="Get my profile",
    response_model=CurrentUserProfileResponses,
    tags=["Account"],
)
@account_bp.route("/profile", methods=["GET"])
@auth.require_auth()
def get_my_profile():
    db = get_core_db()
    actor: User = _users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    claims = auth.get_current_claims()
    profile = CurrentUserProfileResponses(
        id=actor.id,
        auth0_user_id=actor.auth0_user_id,
        email=actor.email,
        display_name=actor.display_name,
        email_verified=bool(claims.get("email_verified", False)),
    )
    return profile.model_dump(mode="json"), 200


@openapi_route(
    summary="Update my profile",
    response_model=CurrentUserResponses,
    request_model=UpdateProfileRequest,
    tags=["Account"],
)
@account_bp.route("/profile", methods=["PATCH"])
@auth.require_auth()
def update_my_profile():
    db = get_core_db()
    actor: User = _users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    data = parse(UpdateProfileRequest, request)
    updated = account_service.update_profile(db=db, actor=actor, data=data, mgmt=auth.mgmt)
    return CurrentUserResponses.model_validate(updated).model_dump(mode="json"), 200


@openapi_route(
    summary="Change email",
    request_model=ChangeEmailRequest,
    tags=["Account"],
)
@account_bp.route("/change-email", methods=["POST"])
@auth.require_auth()
def change_email():
    db = get_core_db()
    actor: User = _users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    data = parse(ChangeEmailRequest, request)
    account_service.change_email(db=db, actor=actor, data=data, mgmt=auth.mgmt)
    return {}, 204


@openapi_route(
    summary="Change username",
    request_model=ChangeUsernameRequest,
    tags=["Account"],
)
@account_bp.route("/change-username", methods=["POST"])
@auth.require_auth()
def change_username():
    db = get_core_db()
    actor: User = _users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    data = parse(ChangeUsernameRequest, request)
    account_service.change_username(actor=actor, data=data, mgmt=auth.mgmt)
    return {}, 204


@openapi_route(
    summary="Change password",
    response_model=PasswordChangeTicketResponses,
    tags=["Account"],
)
@account_bp.route("/change-password", methods=["POST"])
@auth.require_auth()
def change_password():
    db = get_core_db()
    actor: User = _users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    ticket_url = account_service.change_password(actor=actor, mgmt=auth.mgmt)
    return PasswordChangeTicketResponses(ticket_url=ticket_url).model_dump(mode="json"), 200


@openapi_route(
    summary="Clear MFA devices",
    tags=["Account"],
)
@account_bp.route("/clear-mfa", methods=["POST"])
@auth.require_auth()
def clear_mfa():
    db = get_core_db()
    actor: User = _users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    account_service.clear_mfa_devices(actor=actor, mgmt=auth.mgmt)
    return {}, 204


@openapi_route(
    summary="Resend email verification",
    tags=["Account"],
)
@account_bp.route("/resend-verification", methods=["POST"])
@auth.require_auth()
def resend_verification():
    db = get_core_db()
    actor: User = _users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    account_service.resend_verification_email(actor=actor, mgmt=auth.mgmt)
    return {}, 204


@openapi_route(
    summary="Delete my account",
    tags=["Account"],
)
@account_bp.route("", methods=["DELETE"])
@auth.require_auth()
def delete_my_account():
    db = get_core_db()
    actor: User = _users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    account_service.delete_account(db=db, actor=actor, mgmt=auth.mgmt)
    return {}, 204
