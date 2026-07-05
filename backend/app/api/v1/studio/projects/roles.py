from flask import g, request

from app.api.utils.validation import parse
from app.api.v1.studio.projects import roles_service, studio_projects_bp
from app.core.extensions import auth
from app.db.context import get_core_db
from app.domain.permissions import PERMISSIONS
from app.openapi import openapi_route
from app.schema.api.requests.projects import CreateProjectRoleRequest, UpdateProjectRoleRequest
from app.schema.api.responses.projects import ProjectRoleResponses
from app.services.access.access_service import require_project_permission


@openapi_route(summary="List project roles", response_model=list[ProjectRoleResponses], tags=["Roles"])
@studio_projects_bp.route("/<bint:project_id>/roles", methods=["GET"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_roles)
def list_roles(project_id: int):
    roles = roles_service.list_project_roles(db=get_core_db(), project_id=project_id, actor=g.actor)
    return [ProjectRoleResponses.from_orm_with_permissions(r).model_dump(mode="json") for r in roles], 200


@openapi_route(
    summary="Create project role",
    request_model=CreateProjectRoleRequest,
    response_model=ProjectRoleResponses,
    status_code=201,
    tags=["Roles"],
)
@studio_projects_bp.route("/<bint:project_id>/roles", methods=["POST"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_roles)
def create_role(project_id: int):
    payload = parse(CreateProjectRoleRequest, request)
    role = roles_service.create_role(db=get_core_db(), project_id=project_id, data=payload, actor=g.actor)
    return ProjectRoleResponses.from_orm_with_permissions(role).model_dump(mode="json"), 201


@openapi_route(
    summary="Update project role",
    request_model=UpdateProjectRoleRequest,
    response_model=ProjectRoleResponses,
    tags=["Roles"],
)
@studio_projects_bp.route("/<bint:project_id>/roles/<bint:role_id>", methods=["PATCH"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_roles)
def update_role(project_id: int, role_id: int):
    payload = parse(UpdateProjectRoleRequest, request)
    role = roles_service.update_role(
        db=get_core_db(), project_id=project_id, role_id=role_id, data=payload, actor=g.actor
    )
    return ProjectRoleResponses.from_orm_with_permissions(role).model_dump(mode="json"), 200


@openapi_route(summary="Delete project role", tags=["Roles"])
@studio_projects_bp.route("/<bint:project_id>/roles/<bint:role_id>", methods=["DELETE"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_roles)
def delete_role(project_id: int, role_id: int):
    roles_service.delete_role(db=get_core_db(), project_id=project_id, role_id=role_id, actor=g.actor)
    return {}, 204
