from flask import request

from app.api.utils.validation import parse
from app.api.v1.projects import projects_bp, users_service
from app.core.extensions import auth
from app.db.context import get_core_db
from app.openapi import openapi_route
from app.schema.api.requests.surveys_access import CreateSurveyRoleRequest, UpdateSurveyRoleRequest
from app.schema.api.responses.surveys_access import SurveyRoleOut
from app.schema.orm.core.user import User
from app.services.survey_roles import survey_roles_service


@openapi_route(summary="List survey roles", response_model=list[SurveyRoleOut], tags=["Survey Roles"])
@projects_bp.route("/<bint:project_id>/survey-roles", methods=["GET"])
@auth.require_auth()
def list_survey_roles(project_id: int):
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    roles = survey_roles_service.list_survey_roles(db=db, project_id=project_id, actor=actor)
    return [SurveyRoleOut.from_orm_with_permissions(r).model_dump(mode="json") for r in roles], 200


@openapi_route(
    summary="Create survey role",
    request_model=CreateSurveyRoleRequest,
    response_model=SurveyRoleOut,
    status_code=201,
    tags=["Survey Roles"],
)
@projects_bp.route("/<bint:project_id>/survey-roles", methods=["POST"])
@auth.require_auth()
def create_survey_role(project_id: int):
    payload = parse(CreateSurveyRoleRequest, request)
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    role = survey_roles_service.create_role(db=db, project_id=project_id, data=payload, actor=actor)
    return SurveyRoleOut.from_orm_with_permissions(role).model_dump(mode="json"), 201


@openapi_route(
    summary="Update survey role",
    request_model=UpdateSurveyRoleRequest,
    response_model=SurveyRoleOut,
    tags=["Survey Roles"],
)
@projects_bp.route("/<bint:project_id>/survey-roles/<bint:role_id>", methods=["PATCH"])
@auth.require_auth()
def update_survey_role(project_id: int, role_id: int):
    payload = parse(UpdateSurveyRoleRequest, request)
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    role = survey_roles_service.update_role(
        db=db, project_id=project_id, role_id=role_id, data=payload, actor=actor
    )
    return SurveyRoleOut.from_orm_with_permissions(role).model_dump(mode="json"), 200


@openapi_route(summary="Delete survey role", tags=["Survey Roles"])
@projects_bp.route("/<bint:project_id>/survey-roles/<bint:role_id>", methods=["DELETE"])
@auth.require_auth()
def delete_survey_role(project_id: int, role_id: int):
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    survey_roles_service.delete_role(db=db, project_id=project_id, role_id=role_id, actor=actor)
    return {}, 204
