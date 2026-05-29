from flask import Blueprint, request

from app.api.utils.validation import parse
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
from app.schema.api.responses.projects import ProjectInvitationResponses, ProjectMemberResponses
from app.schema.orm.core.user import User
from app.services.account import account_service
from app.services.members import members_service
from app.services.users import UserService

me_bp = Blueprint("me_v1", __name__)

_users_service = UserService()


@openapi_route(
    summary="Get my profile",
    response_model=CurrentUserProfileResponses,
    tags=["Me"],
)
@me_bp.route("/profile", methods=["GET"])
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
    tags=["Me"],
)
@me_bp.route("/profile", methods=["PATCH"])
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
    tags=["Me"],
)
@me_bp.route("/change-email", methods=["POST"])
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
    tags=["Me"],
)
@me_bp.route("/change-username", methods=["POST"])
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
    tags=["Me"],
)
@me_bp.route("/change-password", methods=["POST"])
@auth.require_auth()
def change_password():
    db = get_core_db()
    actor: User = _users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    ticket_url = account_service.change_password(actor=actor, mgmt=auth.mgmt)
    return PasswordChangeTicketResponses(ticket_url=ticket_url).model_dump(mode="json"), 200


@openapi_route(
    summary="Clear MFA devices",
    tags=["Me"],
)
@me_bp.route("/clear-mfa", methods=["POST"])
@auth.require_auth()
def clear_mfa():
    db = get_core_db()
    actor: User = _users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    account_service.clear_mfa_devices(actor=actor, mgmt=auth.mgmt)
    return {}, 204


@openapi_route(
    summary="Resend email verification",
    tags=["Me"],
)
@me_bp.route("/resend-verification", methods=["POST"])
@auth.require_auth()
def resend_verification():
    db = get_core_db()
    actor: User = _users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    account_service.resend_verification_email(actor=actor, mgmt=auth.mgmt)
    return {}, 204


@openapi_route(
    summary="Delete my account",
    tags=["Me"],
)
@me_bp.route("", methods=["DELETE"])
@auth.require_auth()
def delete_my_account():
    db = get_core_db()
    actor: User = _users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    account_service.delete_account(db=db, actor=actor, mgmt=auth.mgmt)
    return {}, 204


@openapi_route(
    summary="Get my invitations",
    response_model=list[ProjectInvitationResponses],
    tags=["Me"],
)
@me_bp.route("/invitations", methods=["GET"])
@auth.require_auth()
def get_my_invitations():
    db = get_core_db()
    actor: User = _users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    invitations = members_service.get_my_invitations(db=db, actor=actor)
    return [ProjectInvitationResponses.from_orm_with_project(i).model_dump(mode="json") for i in invitations], 200


@openapi_route(
    summary="Accept invitation",
    response_model=ProjectMemberResponses,
    status_code=200,
    tags=["Me"],
)
@me_bp.route("/invitations/<bint:invitation_id>/accept", methods=["POST"])
@auth.require_auth()
def accept_invitation(invitation_id: int):
    db = get_core_db()
    actor: User = _users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    membership = members_service.accept_invitation(db=db, invitation_id=invitation_id, actor=actor)
    return ProjectMemberResponses.model_validate(membership).model_dump(mode="json"), 200


@openapi_route(
    summary="Decline invitation",
    tags=["Me"],
)
@me_bp.route("/invitations/<bint:invitation_id>/decline", methods=["POST"])
@auth.require_auth()
def decline_invitation(invitation_id: int):
    db = get_core_db()
    actor: User = _users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    members_service.decline_invitation(db=db, invitation_id=invitation_id, actor=actor)
    return {}, 204
