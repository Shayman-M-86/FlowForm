from flask import g, request

from app.api.utils.validation import parse
from app.api.v1.studio.projects import members_service, studio_projects_bp
from app.core.extensions import auth
from app.db.context import get_core_db
from app.domain.permissions import PERMISSIONS
from app.openapi import openapi_route
from app.schema.api.requests.projects import SendInvitationRequest
from app.schema.api.responses.projects import ProjectInvitationResponses
from app.services.access.access_service import require_project_permission


@openapi_route(
    summary="List project invitations",
    response_model=list[ProjectInvitationResponses],
    tags=["Project Invitations"],
)
@studio_projects_bp.route("/<bint:project_id>/invitations", methods=["GET"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_members)
def list_invitations(project_id: int):
    invitations = members_service.list_project_invitations(db=get_core_db(), project_id=project_id, actor=g.actor)
    return [ProjectInvitationResponses.model_validate(i).model_dump(mode="json") for i in invitations], 200


@openapi_route(
    summary="Invite project member",
    request_model=SendInvitationRequest,
    response_model=ProjectInvitationResponses,
    status_code=201,
    tags=["Project Invitations"],
)
@studio_projects_bp.route("/<bint:project_id>/invitations", methods=["POST"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_members)
def send_invitation(project_id: int):
    payload = parse(SendInvitationRequest, request)
    invitation = members_service.send_invitation(db=get_core_db(), project_id=project_id, data=payload, actor=g.actor)
    return ProjectInvitationResponses.model_validate(invitation).model_dump(mode="json"), 201


@openapi_route(
    summary="Revoke project invitation",
    tags=["Project Invitations"],
)
@studio_projects_bp.route("/<bint:project_id>/invitations/<bint:invitation_id>", methods=["DELETE"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_members)
def revoke_invitation(project_id: int, invitation_id: int):
    members_service.revoke_invitation(
        db=get_core_db(), project_id=project_id, invitation_id=invitation_id, actor=g.actor
    )
    return {}, 204
