from flask import request

from app.api.utils.validation import parse
from app.api.v1.projects import projects_bp, users_service
from app.core.extensions import auth
from app.db.context import get_core_db
from app.openapi import openapi_route
from app.schema.api.requests.surveys_access import AssignSurveyMemberRoleRequest, UpdateSurveyMemberRoleRequest
from app.schema.api.responses.surveys_access import SurveyMemberRoleOut
from app.schema.orm.core.user import User
from app.services.survey_members import survey_members_service


@openapi_route(
    summary="List survey member role assignments",
    response_model=list[SurveyMemberRoleOut],
    tags=["Survey Members"],
)
@projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/members", methods=["GET"])
@auth.require_auth()
def list_survey_members(project_id: int, survey_id: int):
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    assignments = survey_members_service.list_survey_members(
        db=db, project_id=project_id, survey_id=survey_id, actor=actor
    )
    return [SurveyMemberRoleOut.from_assignment(a).model_dump(mode="json") for a in assignments], 200


@openapi_route(
    summary="Assign survey role to member",
    request_model=AssignSurveyMemberRoleRequest,
    response_model=SurveyMemberRoleOut,
    status_code=201,
    tags=["Survey Members"],
)
@projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/members", methods=["POST"])
@auth.require_auth()
def assign_survey_member_role(project_id: int, survey_id: int):
    payload = parse(AssignSurveyMemberRoleRequest, request)
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    assignment = survey_members_service.assign_member_role(
        db=db, project_id=project_id, survey_id=survey_id, data=payload, actor=actor
    )
    return SurveyMemberRoleOut.from_assignment(assignment).model_dump(mode="json"), 201


@openapi_route(
    summary="Update survey member role assignment",
    request_model=UpdateSurveyMemberRoleRequest,
    response_model=SurveyMemberRoleOut,
    tags=["Survey Members"],
)
@projects_bp.route(
    "/<bint:project_id>/surveys/<bint:survey_id>/members/<bint:membership_id>",
    methods=["PATCH"],
)
@auth.require_auth()
def update_survey_member_role(project_id: int, survey_id: int, membership_id: int):
    payload = parse(UpdateSurveyMemberRoleRequest, request)
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    assignment = survey_members_service.update_member_role(
        db=db,
        project_id=project_id,
        survey_id=survey_id,
        membership_id=membership_id,
        data=payload,
        actor=actor,
    )
    return SurveyMemberRoleOut.from_assignment(assignment).model_dump(mode="json"), 200


@openapi_route(summary="Remove survey member role assignment", tags=["Survey Members"])
@projects_bp.route(
    "/<bint:project_id>/surveys/<bint:survey_id>/members/<bint:membership_id>",
    methods=["DELETE"],
)
@auth.require_auth()
def remove_survey_member_role(project_id: int, survey_id: int, membership_id: int):
    db = get_core_db()
    actor: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    survey_members_service.remove_member_role(
        db=db, project_id=project_id, survey_id=survey_id, membership_id=membership_id, actor=actor
    )
    return {}, 204
