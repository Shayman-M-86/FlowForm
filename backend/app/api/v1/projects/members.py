from flask import request

from app.api.utils.validation import parse
from app.api.v1.projects import members_service, projects_bp, users_service
from app.core.extensions import auth
from app.db.context import get_core_db
from app.openapi import openapi_route
from app.schema.api.requests.projects import SendInvitationRequest, UpdateMemberRequest
from app.schema.api.responses.projects import ProjectInvitationResponses, ProjectMemberResponses
from app.schema.orm.core.user import User


@openapi_route(summary="List project members", response_model=list[ProjectMemberResponses], tags=["Members"])
@projects_bp.route("/<bint:project_id>/members", methods=["GET"])
@auth.require_auth()
def list_members(project_id: int):
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    members = members_service.list_project_members(db=db, project_id=project_id, actor=actor)
    return [ProjectMemberResponses.model_validate(m).model_dump(mode="json") for m in members], 200


@openapi_route(
    summary="List project invitations",
    response_model=list[ProjectInvitationResponses],
    tags=["Members"],
)
@projects_bp.route("/<bint:project_id>/invitations", methods=["GET"])
@auth.require_auth()
def list_invitations(project_id: int):
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    invitations = members_service.list_project_invitations(db=db, project_id=project_id, actor=actor)
    return [ProjectInvitationResponses.model_validate(i).model_dump(mode="json") for i in invitations], 200


@openapi_route(
    summary="Invite member",
    request_model=SendInvitationRequest,
    response_model=ProjectInvitationResponses,
    status_code=201,
    tags=["Members"],
)
@projects_bp.route("/<bint:project_id>/invitations", methods=["POST"])
@auth.require_auth()
def send_invitation(project_id: int):
    payload = parse(SendInvitationRequest, request)
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    invitation = members_service.send_invitation(db=db, project_id=project_id, data=payload, actor=actor)
    return ProjectInvitationResponses.model_validate(invitation).model_dump(mode="json"), 201


@openapi_route(
    summary="Revoke invitation",
    tags=["Members"],
)
@projects_bp.route("/<bint:project_id>/invitations/<bint:invitation_id>", methods=["DELETE"])
@auth.require_auth()
def revoke_invitation(project_id: int, invitation_id: int):
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    members_service.revoke_invitation(db=db, project_id=project_id, invitation_id=invitation_id, actor=actor)
    return {}, 204


@openapi_route(
    summary="Update member",
    request_model=UpdateMemberRequest,
    response_model=ProjectMemberResponses,
    tags=["Members"],
)
@projects_bp.route("/<bint:project_id>/members/<bint:membership_id>", methods=["PATCH"])
@auth.require_auth()
def update_member(project_id: int, membership_id: int):
    payload = parse(UpdateMemberRequest, request)
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    membership = members_service.update_member(
        db=db, project_id=project_id, membership_id=membership_id, data=payload, actor=actor
    )
    return ProjectMemberResponses.model_validate(membership).model_dump(mode="json"), 200


@openapi_route(summary="Remove member", tags=["Members"])
@projects_bp.route("/<bint:project_id>/members/<bint:membership_id>", methods=["DELETE"])
@auth.require_auth()
def remove_member(project_id: int, membership_id: int):
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    members_service.remove_member(db=db, project_id=project_id, membership_id=membership_id, actor=actor)
    return {}, 204
