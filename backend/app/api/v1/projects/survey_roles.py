from flask import g, request

from app.api.utils.validation import parse
from app.api.v1.projects import projects_bp
from app.core.extensions import auth
from app.db.context import get_core_db
from app.domain.permissions import PERMISSIONS
from app.openapi import openapi_route
from app.schema.api.requests.surveys_access import CreateSurveyRoleRequest, UpdateSurveyRoleRequest
from app.schema.api.responses.surveys_access import SurveyRoleResponses
from app.services.access.access_service import require_project_permission
from app.services.survey_roles import survey_roles_service


@openapi_route(summary="List survey roles", response_model=list[SurveyRoleResponses], tags=["Survey Roles"])
@projects_bp.route("/<bint:project_id>/survey-roles", methods=["GET"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_roles)
def list_survey_roles(project_id: int):
    roles = survey_roles_service.list_survey_roles(db=get_core_db(), project_id=project_id, actor=g.actor)
    return [SurveyRoleResponses.from_orm_with_permissions(r).model_dump(mode="json") for r in roles], 200


@openapi_route(
    summary="Create survey role",
    request_model=CreateSurveyRoleRequest,
    response_model=SurveyRoleResponses,
    status_code=201,
    tags=["Survey Roles"],
)
@projects_bp.route("/<bint:project_id>/survey-roles", methods=["POST"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_roles)
def create_survey_role(project_id: int):
    payload = parse(CreateSurveyRoleRequest, request)
    role = survey_roles_service.create_role(db=get_core_db(), project_id=project_id, data=payload, actor=g.actor)
    return SurveyRoleResponses.from_orm_with_permissions(role).model_dump(mode="json"), 201


@openapi_route(
    summary="Update survey role",
    request_model=UpdateSurveyRoleRequest,
    response_model=SurveyRoleResponses,
    tags=["Survey Roles"],
)
@projects_bp.route("/<bint:project_id>/survey-roles/<bint:role_id>", methods=["PATCH"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_roles)
def update_survey_role(project_id: int, role_id: int):
    payload = parse(UpdateSurveyRoleRequest, request)
    role = survey_roles_service.update_role(
        db=get_core_db(), project_id=project_id, role_id=role_id, data=payload, actor=g.actor
    )
    return SurveyRoleResponses.from_orm_with_permissions(role).model_dump(mode="json"), 200


@openapi_route(summary="Delete survey role", tags=["Survey Roles"])
@projects_bp.route("/<bint:project_id>/survey-roles/<bint:role_id>", methods=["DELETE"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_roles)
def delete_survey_role(project_id: int, role_id: int):
    survey_roles_service.delete_role(db=get_core_db(), project_id=project_id, role_id=role_id, actor=g.actor)
    return {}, 204
