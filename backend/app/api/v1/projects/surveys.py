from flask import request

from app.api.utils.validation import parse
from app.api.v1.projects import projects_bp, survey_service, users_service
from app.api.v1.projects.resolver import resolve_project_ref
from app.core.extensions import auth
from app.db.context import get_core_db
from app.schema.api.requests.surveys import CreateSurveyRequest, UpdateSurveyRequest
from app.schema.api.responses.surveys import SurveyOut
from app.schema.orm.core.user import User


@projects_bp.route("/<project_ref>/surveys", methods=["GET"])
@auth.require_auth()
def list_surveys(project_ref: str):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    surveys = survey_service.list_surveys(db, project_id=project_id, actor=user)
    return [SurveyOut.model_validate(s).model_dump(mode="json") for s in surveys], 200


@projects_bp.route("/<project_ref>/surveys", methods=["POST"])
@auth.require_auth()
def create_survey(project_ref: str):
    payload = parse(CreateSurveyRequest, request)
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    survey = survey_service.create_survey(db=db, project_id=project_id, data=payload, actor=user)
    return SurveyOut.model_validate(survey).model_dump(mode="json"), 201


@projects_bp.route("/<project_ref>/surveys/<int:survey_id>", methods=["GET"])
@auth.require_auth()
def get_survey(project_ref: str, survey_id: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    survey = survey_service.get_survey(db=db, project_id=project_id, survey_id=survey_id, actor=user)
    return SurveyOut.model_validate(survey).model_dump(mode="json"), 200


@projects_bp.route("/<project_ref>/surveys/<int:survey_id>", methods=["PATCH"])
@auth.require_auth()
def update_survey(project_ref: str, survey_id: int):
    payload = parse(UpdateSurveyRequest, request)
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    survey = survey_service.update_survey(db=db, project_id=project_id, survey_id=survey_id, data=payload, actor=user)
    return SurveyOut.model_validate(survey).model_dump(mode="json"), 200


@projects_bp.route("/<project_ref>/surveys/<int:survey_id>", methods=["DELETE"])
@auth.require_auth()
def delete_survey(project_ref: str, survey_id: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    survey_service.delete_survey(db=db, project_id=project_id, survey_id=survey_id, actor=user)
    return {"message": "Survey deleted"}, 200
