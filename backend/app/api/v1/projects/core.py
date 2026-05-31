from flask import g, request

from app.api.utils.validation import parse
from app.api.v1.projects import project_service, projects_bp
from app.core.extensions import auth
from app.db.context import get_core_db
from app.domain.permissions import PERMISSIONS
from app.openapi import openapi_route
from app.schema.api.requests.projects import CreateProjectRequest, UpdateProjectRequest
from app.schema.api.responses.projects import MyProjectPermissionsResponses, ProjectResponses
from app.services.access.access_service import access_service, require_project_permission
from app.services.users import UserService

_users_service = UserService()


@openapi_route(summary="List projects", response_model=list[ProjectResponses], tags=["Projects"])
@projects_bp.route("", methods=["GET"])
@auth.require_auth()
def list_projects():
    actor = _users_service.get_user_by_sub(db=get_core_db(), auth0_user_id=auth.get_current_user_sub())
    g.actor = actor
    projects = project_service.list_projects(db=get_core_db(), actor=actor)
    return [ProjectResponses.model_validate(p).model_dump(mode="json") for p in projects], 200


@openapi_route(
    summary="Create project",
    request_model=CreateProjectRequest,
    response_model=ProjectResponses,
    status_code=201,
    tags=["Projects"],
)
@projects_bp.route("", methods=["POST"])
@auth.require_auth()
def create_project():
    payload = parse(CreateProjectRequest, request)
    actor = _users_service.get_user_by_sub(db=get_core_db(), auth0_user_id=auth.get_current_user_sub())
    g.actor = actor
    project = project_service.create_project(db=get_core_db(), data=payload, actor=actor)
    return ProjectResponses.model_validate(project).model_dump(mode="json"), 201


@openapi_route(summary="Get project", response_model=ProjectResponses, tags=["Projects"])
@projects_bp.route("/<bint:project_id>", methods=["GET"])
@auth.require_auth()
def get_project(project_id: int):
    actor = _users_service.get_user_by_sub(db=get_core_db(), auth0_user_id=auth.get_current_user_sub())
    g.actor = actor
    project = project_service.get_project(db=get_core_db(), project_id=project_id, actor=actor)
    return ProjectResponses.model_validate(project).model_dump(mode="json"), 200


@openapi_route(summary="Get my project permissions", response_model=MyProjectPermissionsResponses, tags=["Projects"])
@projects_bp.route("/<bint:project_id>/my-permissions", methods=["GET"])
@auth.require_auth()
def get_my_project_permissions(project_id: int):
    db = get_core_db()
    actor = _users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    g.actor = actor
    project_access = access_service.get_project_access(db=db, project_id=project_id, user_id=actor.id)
    return MyProjectPermissionsResponses.model_validate({"permissions": sorted(project_access.permissions)}).model_dump(
        mode="json"
    ), 200


@openapi_route(
    summary="Update project",
    request_model=UpdateProjectRequest,
    response_model=ProjectResponses,
    tags=["Projects"],
)
@projects_bp.route("/<bint:project_id>", methods=["PATCH"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.edit)
def update_project(project_id: int):
    payload = parse(UpdateProjectRequest, request)
    project = project_service.update_project(db=get_core_db(), project_id=project_id, data=payload, actor=g.actor)
    return ProjectResponses.model_validate(project).model_dump(mode="json"), 200


@openapi_route(summary="Delete project", tags=["Projects"], status_code=204)
@projects_bp.route("/<bint:project_id>", methods=["DELETE"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.delete)
def delete_project(project_id: int):
    project_service.delete_project(db=get_core_db(), project_id=project_id, actor=g.actor)
    return "", 204
