from flask import request

from app.api.utils.validation import parse
from app.api.v1.projects import project_service, projects_bp, users_service
from app.core.extensions import auth
from app.db.context import get_core_db
from app.openapi import openapi_route
from app.schema.api.requests.projects import CreateProjectRequest, UpdateProjectRequest
from app.schema.api.responses.projects import MyProjectPermissionsOut, ProjectOut
from app.schema.orm.core.user import User
from app.services.access.access_service import access_service


@openapi_route(summary="List projects", response_model=list[ProjectOut], tags=["Projects"])
@projects_bp.route("", methods=["GET"])
@auth.require_auth()
def list_projects():
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    projects = project_service.list_projects(db=db, actor=actor)
    return [ProjectOut.model_validate(p).model_dump(mode="json") for p in projects], 200


@openapi_route(
    summary="Create project",
    request_model=CreateProjectRequest,
    response_model=ProjectOut,
    status_code=201,
    tags=["Projects"],
)
@projects_bp.route("", methods=["POST"])
@auth.require_auth()
def create_project():
    payload = parse(CreateProjectRequest, request)
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project = project_service.create_project(db=db, data=payload, actor=actor)
    return ProjectOut.model_validate(project).model_dump(mode="json"), 201


@openapi_route(summary="Get project", response_model=ProjectOut, tags=["Projects"])
@projects_bp.route("/<bint:project_id>", methods=["GET"])
@auth.require_auth()
def get_project(project_id: int):
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project = project_service.get_project(db=db, project_id=project_id, actor=actor)
    return ProjectOut.model_validate(project).model_dump(mode="json"), 200


@openapi_route(summary="Get my project permissions", response_model=MyProjectPermissionsOut, tags=["Projects"])
@projects_bp.route("/<bint:project_id>/my-permissions", methods=["GET"])
@auth.require_auth()
def get_my_project_permissions(project_id: int):
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_access = access_service.get_project_access(db=db, project_id=project_id, user_id=actor.id)
    return MyProjectPermissionsOut.model_validate({"permissions": sorted(project_access.permissions)}).model_dump(mode="json"), 200


@openapi_route(
    summary="Update project",
    request_model=UpdateProjectRequest,
    response_model=ProjectOut,
    tags=["Projects"],
)
@projects_bp.route("/<bint:project_id>", methods=["PATCH"])
@auth.require_auth()
def update_project(project_id: int):
    payload = parse(UpdateProjectRequest, request)
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project = project_service.update_project(db=db, project_id=project_id, data=payload, actor=actor)
    return ProjectOut.model_validate(project).model_dump(mode="json"), 200


@openapi_route(summary="Delete project", tags=["Projects"], status_code=204)
@projects_bp.route("/<bint:project_id>", methods=["DELETE"])
@auth.require_auth()
def delete_project(project_id: int):
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_service.delete_project(db=db, project_id=project_id, actor=actor)
    return "", 204
