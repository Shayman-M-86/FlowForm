from flask import g, request

from app.api.utils.validation import parse
from app.api.v1.projects import projects_bp
from app.core.extensions import auth
from app.db.context import get_core_db
from app.domain.permissions import PERMISSIONS
from app.openapi import openapi_route
from app.schema.api.requests.surveys_access import AssignSurveyMemberRoleRequest, UpdateSurveyMemberRoleRequest
from app.schema.api.responses.surveys_access import SurveyMemberRoleResponses
from app.services.access.access_service import require_project_permission
from app.services.survey_members import survey_members_service


@openapi_route(
    summary="List survey member role assignments",
    response_model=list[SurveyMemberRoleResponses],
    tags=["Survey Members"],
)
@projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/members", methods=["GET"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_members)
def list_survey_members(project_id: int, survey_id: int):
    assignments = survey_members_service.list_survey_members(
        db=get_core_db(), project_id=project_id, survey_id=survey_id, actor=g.actor
    )
    return [SurveyMemberRoleResponses.from_assignment(a).model_dump(mode="json") for a in assignments], 200


@openapi_route(
    summary="Assign survey role to member",
    request_model=AssignSurveyMemberRoleRequest,
    response_model=SurveyMemberRoleResponses,
    status_code=201,
    tags=["Survey Members"],
)
@projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/members", methods=["POST"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_members)
def assign_survey_member_role(project_id: int, survey_id: int):
    payload = parse(AssignSurveyMemberRoleRequest, request)
    assignment = survey_members_service.assign_member_role(
        db=get_core_db(), project_id=project_id, survey_id=survey_id, data=payload, actor=g.actor
    )
    return SurveyMemberRoleResponses.from_assignment(assignment).model_dump(mode="json"), 201


@openapi_route(
    summary="Update survey member role assignment",
    request_model=UpdateSurveyMemberRoleRequest,
    response_model=SurveyMemberRoleResponses,
    tags=["Survey Members"],
)
@projects_bp.route(
    "/<bint:project_id>/surveys/<bint:survey_id>/members/<bint:membership_id>",
    methods=["PATCH"],
)
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_members)
def update_survey_member_role(project_id: int, survey_id: int, membership_id: int):
    payload = parse(UpdateSurveyMemberRoleRequest, request)
    assignment = survey_members_service.update_member_role(
        db=get_core_db(),
        project_id=project_id,
        survey_id=survey_id,
        membership_id=membership_id,
        data=payload,
        actor=g.actor,
    )
    return SurveyMemberRoleResponses.from_assignment(assignment).model_dump(mode="json"), 200


@openapi_route(summary="Remove survey member role assignment", tags=["Survey Members"])
@projects_bp.route(
    "/<bint:project_id>/surveys/<bint:survey_id>/members/<bint:membership_id>",
    methods=["DELETE"],
)
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_members)
def remove_survey_member_role(project_id: int, survey_id: int, membership_id: int):
    survey_members_service.remove_member_role(
        db=get_core_db(), project_id=project_id, survey_id=survey_id, membership_id=membership_id, actor=g.actor
    )
    return {}, 204
