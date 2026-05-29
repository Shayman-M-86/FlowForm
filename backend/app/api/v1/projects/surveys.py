from flask import request

from app.api.utils.validation import parse
from app.api.v1.projects import projects_bp, survey_service, users_service
from app.core.extensions import auth
from app.db.context import get_core_db
from app.openapi import openapi_route
from app.schema.api.requests.surveys import CreateSurveyRequest, UpdateSurveyRequest
from app.schema.api.responses.surveys import SurveyResponses
from app.schema.orm.core.user import User


@openapi_route(summary="List surveys", response_model=list[SurveyResponses], tags=["Surveys"])
@projects_bp.route("/<bint:project_id>/surveys", methods=["GET"])
@auth.require_auth()
def list_surveys(project_id: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    surveys = survey_service.list_surveys(db, project_id=project_id, actor=user)
    return [SurveyResponses.model_validate(s).model_dump(mode="json") for s in surveys], 200


@openapi_route(
    summary="Create survey",
    request_model=CreateSurveyRequest,
    response_model=SurveyResponses,
    status_code=201,
    tags=["Surveys"],
)
@projects_bp.route("/<bint:project_id>/surveys", methods=["POST"])
@auth.require_auth()
def create_survey(project_id: int):
    payload = parse(CreateSurveyRequest, request)
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    survey = survey_service.create_survey(db=db, project_id=project_id, data=payload, actor=user)
    return SurveyResponses.model_validate(survey).model_dump(mode="json"), 201


@openapi_route(summary="Get survey", response_model=SurveyResponses, tags=["Surveys"])
@projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>", methods=["GET"])
@auth.require_auth()
def get_survey(project_id: int, survey_id: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    survey = survey_service.get_survey(db=db, project_id=project_id, survey_id=survey_id, actor=user)
    return SurveyResponses.model_validate(survey).model_dump(mode="json"), 200


@openapi_route(
    summary="Update survey",
    request_model=UpdateSurveyRequest,
    response_model=SurveyResponses,
    tags=["Surveys"],
)
@projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>", methods=["PATCH"])
@auth.require_auth()
def update_survey(project_id: int, survey_id: int):
    payload = parse(UpdateSurveyRequest, request)
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    survey = survey_service.update_survey(db=db, project_id=project_id, survey_id=survey_id, data=payload, actor=user)
    return SurveyResponses.model_validate(survey).model_dump(mode="json"), 200


@openapi_route(summary="Delete survey", tags=["Surveys"], status_code=204)
@projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>", methods=["DELETE"])
@auth.require_auth()
def delete_survey(project_id: int, survey_id: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    survey_service.delete_survey(db=db, project_id=project_id, survey_id=survey_id, actor=user)
    return "", 204
