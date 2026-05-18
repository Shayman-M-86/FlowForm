from flask import request

from app.api.utils.validation import parse
from app.api.v1.projects import project_service, projects_bp, users_service
from app.api.v1.projects.resolver import resolve_project_ref
from app.core.extensions import auth
from app.db.context import get_core_db
from app.openapi import openapi_route
from app.schema.api.requests.projects import CreateProjectRequest, UpdateProjectRequest
from app.schema.api.responses.projects import ProjectOut
from app.schema.orm.core.user import User


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
@projects_bp.route("/<project_ref>", methods=["GET"])
@auth.require_auth()
def get_project(project_ref: str):
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project = resolve_project_ref(db, project_ref, actor)
    return ProjectOut.model_validate(project).model_dump(mode="json"), 200


@openapi_route(
    summary="Update project",
    request_model=UpdateProjectRequest,
    response_model=ProjectOut,
    tags=["Projects"],
)
@projects_bp.route("/<project_ref>", methods=["PATCH"])
@auth.require_auth()
def update_project(project_ref: str):
    payload = parse(UpdateProjectRequest, request)
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, actor).id
    project = project_service.update_project(db=db, project_id=project_id, data=payload, actor=actor)
    return ProjectOut.model_validate(project).model_dump(mode="json"), 200


@openapi_route(summary="Delete project", tags=["Projects"])
@projects_bp.route("/<project_ref>", methods=["DELETE"])
@auth.require_auth()
def delete_project(project_ref: str):
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, actor).id
    project_service.delete_project(db=db, project_id=project_id, actor=actor)
    return {"message": "Project deleted"}, 200
