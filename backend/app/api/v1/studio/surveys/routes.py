from flask import g, request

from app.api.utils.validation import parse
from app.api.v1.studio.projects import studio_projects_bp, survey_service, users_service
from app.core.extensions import auth
from app.db.context import get_core_db
from app.domain.permissions import PERMISSIONS
from app.openapi import openapi_route
from app.schema.api.requests.surveys import CreateSurveyRequest, UpdateSurveyRequest
from app.schema.api.responses.surveys import MySurveyPermissionsResponses, SurveyResponses
from app.services.access.access_service import access_service, require_project_permission, require_survey_permission


@openapi_route(summary="List surveys", response_model=list[SurveyResponses], tags=["Surveys"])
@studio_projects_bp.route("/<bint:project_id>/surveys", methods=["GET"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.survey.view)
def list_surveys(project_id: int):
    surveys = survey_service.list_surveys(get_core_db(), project_id=project_id, actor=g.actor)
    return [SurveyResponses.model_validate(s).model_dump(mode="json") for s in surveys], 200


@openapi_route(
    summary="Create survey",
    request_model=CreateSurveyRequest,
    response_model=SurveyResponses,
    status_code=201,
    tags=["Surveys"],
)
@studio_projects_bp.route("/<bint:project_id>/surveys", methods=["POST"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.survey.create)
def create_survey(project_id: int):
    payload = parse(CreateSurveyRequest, request)
    survey = survey_service.create_survey(db=get_core_db(), project_id=project_id, data=payload, actor=g.actor)
    return SurveyResponses.model_validate(survey).model_dump(mode="json"), 201


@openapi_route(summary="Get survey", response_model=SurveyResponses, tags=["Surveys"])
@studio_projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>", methods=["GET"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.view)
def get_survey(project_id: int, survey_id: int):
    survey = survey_service.get_survey(db=get_core_db(), project_id=project_id, survey_id=survey_id, actor=g.actor)
    return SurveyResponses.model_validate(survey).model_dump(mode="json"), 200


@openapi_route(
    summary="Update survey",
    request_model=UpdateSurveyRequest,
    response_model=SurveyResponses,
    tags=["Surveys"],
)
@studio_projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>", methods=["PATCH"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.edit)
def update_survey(project_id: int, survey_id: int):
    payload = parse(UpdateSurveyRequest, request)
    survey = survey_service.update_survey(
        db=get_core_db(), project_id=project_id, survey_id=survey_id, data=payload, actor=g.actor
    )
    return SurveyResponses.model_validate(survey).model_dump(mode="json"), 200


@openapi_route(summary="Delete survey", tags=["Surveys"], status_code=204)
@studio_projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>", methods=["DELETE"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.delete)
def delete_survey(project_id: int, survey_id: int):
    survey_service.delete_survey(db=get_core_db(), project_id=project_id, survey_id=survey_id, actor=g.actor)
    return "", 204


@openapi_route(summary="Get my survey permissions", response_model=MySurveyPermissionsResponses, tags=["Surveys"])
@studio_projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/my-permissions", methods=["GET"])
@auth.require_auth()
def get_my_survey_permissions(project_id: int, survey_id: int):
    db = get_core_db()
    actor = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    g.actor = actor
    survey_access = access_service.get_survey_access(
        db=db, project_id=project_id, survey_id=survey_id, user_id=actor.id
    )
    return MySurveyPermissionsResponses(
        permissions=sorted(survey_access.permissions)  # type: ignore[arg-type]
    ).model_dump(mode="json"), 200
