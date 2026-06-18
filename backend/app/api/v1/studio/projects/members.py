from flask import g, request

from app.api.utils.validation import parse
from app.api.v1.studio.projects import members_service, studio_projects_bp
from app.core.extensions import auth
from app.db.context import get_core_db
from app.domain.permissions import PERMISSIONS
from app.openapi import openapi_route
from app.schema.api.requests.projects import UpdateMemberRequest
from app.schema.api.responses.projects import ProjectMemberResponses
from app.services.access.access_service import require_project_permission


@openapi_route(summary="List project members", response_model=list[ProjectMemberResponses], tags=["Project Members"])
@studio_projects_bp.route("/<bint:project_id>/members", methods=["GET"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_members)
def list_members(project_id: int):
    members = members_service.list_project_members(db=get_core_db(), project_id=project_id, actor=g.actor)
    return [ProjectMemberResponses.model_validate(m).model_dump(mode="json") for m in members], 200


@openapi_route(
    summary="Update project member",
    request_model=UpdateMemberRequest,
    response_model=ProjectMemberResponses,
    tags=["Project Members"],
)
@studio_projects_bp.route("/<bint:project_id>/members/<bint:membership_id>", methods=["PATCH"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_members)
def update_member(project_id: int, membership_id: int):
    payload = parse(UpdateMemberRequest, request)
    membership = members_service.update_member(
        db=get_core_db(), project_id=project_id, membership_id=membership_id, data=payload, actor=g.actor
    )
    return ProjectMemberResponses.model_validate(membership).model_dump(mode="json"), 200


@openapi_route(summary="Remove project member", tags=["Project Members"])
@studio_projects_bp.route("/<bint:project_id>/members/<bint:membership_id>", methods=["DELETE"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_members)
def remove_member(project_id: int, membership_id: int):
    members_service.remove_member(db=get_core_db(), project_id=project_id, membership_id=membership_id, actor=g.actor)
    return {}, 204
