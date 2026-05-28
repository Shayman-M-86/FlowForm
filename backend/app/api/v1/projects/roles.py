from flask import request

from app.api.utils.validation import parse
from app.api.v1.projects import projects_bp, roles_service, users_service
from app.core.extensions import auth
from app.db.context import get_core_db
from app.openapi import openapi_route
from app.schema.api.requests.projects import CreateProjectRoleRequest, UpdateProjectRoleRequest
from app.schema.api.responses.projects import ProjectRoleOut
from app.schema.orm.core.user import User


@openapi_route(summary="List project roles", response_model=list[ProjectRoleOut], tags=["Roles"])
@projects_bp.route("/<bint:project_id>/roles", methods=["GET"])
@auth.require_auth()
def list_roles(project_id: int):
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    roles = roles_service.list_project_roles(db=db, project_id=project_id, actor=actor)
    return [ProjectRoleOut.from_orm_with_permissions(r).model_dump(mode="json") for r in roles], 200


@openapi_route(
    summary="Create project role",
    request_model=CreateProjectRoleRequest,
    response_model=ProjectRoleOut,
    status_code=201,
    tags=["Roles"],
)
@projects_bp.route("/<bint:project_id>/roles", methods=["POST"])
@auth.require_auth()
def create_role(project_id: int):
    payload = parse(CreateProjectRoleRequest, request)
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    role = roles_service.create_role(db=db, project_id=project_id, data=payload, actor=actor)
    return ProjectRoleOut.from_orm_with_permissions(role).model_dump(mode="json"), 201


@openapi_route(
    summary="Update project role",
    request_model=UpdateProjectRoleRequest,
    response_model=ProjectRoleOut,
    tags=["Roles"],
)
@projects_bp.route("/<bint:project_id>/roles/<bint:role_id>", methods=["PATCH"])
@auth.require_auth()
def update_role(project_id: int, role_id: int):
    payload = parse(UpdateProjectRoleRequest, request)
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    role = roles_service.update_role(db=db, project_id=project_id, role_id=role_id, data=payload, actor=actor)
    return ProjectRoleOut.from_orm_with_permissions(role).model_dump(mode="json"), 200


@openapi_route(summary="Delete project role", tags=["Roles"])
@projects_bp.route("/<bint:project_id>/roles/<bint:role_id>", methods=["DELETE"])
@auth.require_auth()
def delete_role(project_id: int, role_id: int):
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    roles_service.delete_role(db=db, project_id=project_id, role_id=role_id, actor=actor)
    return {}, 204
