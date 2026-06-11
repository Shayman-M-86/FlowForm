from uuid import UUID

from flask import request

from app.api.utils.validation import parse, parse_query
from app.api.v1.projects import projects_bp
from app.api.v1.projects.survey_responses_temp import (
    build_placeholder_response_detail,
    build_placeholder_response_export,
    build_placeholder_response_history,
    build_placeholder_response_list,
)
from app.core.extensions import auth
from app.domain.permissions import PERMISSIONS
from app.openapi import openapi_route
from app.schema.api.requests.survey_responses import ExportSurveyResponsesRequest, ListSurveyResponsesRequest
from app.schema.api.responses.survey_responses import (
    PaginatedSurveyResponsesResponses,
    SurveyResponseDetailResponses,
    SurveyResponseExportResponses,
    SurveyResponseHistoryResponses,
)
from app.services.access.access_service import require_survey_permission

# TODO(phase7): Replace these contract stubs with the real admin-read service.
# Every handler must authorise survey access, derive the session locator from
# core metadata, load the response envelope, and decrypt canonical revisions
# through the service path — never bypassing the decrypt/authorisation flow.


@openapi_route(
    summary="List survey responses",
    query_model=ListSurveyResponsesRequest,
    response_model=PaginatedSurveyResponsesResponses,
    tags=["Survey Responses"],
)
@projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/responses", methods=["GET"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.submission.view)
def list_responses(project_id: int, survey_id: int):
    params = parse_query(ListSurveyResponsesRequest, request)
    response = build_placeholder_response_list(page=params.page, page_size=params.page_size)
    return response.model_dump(mode="json"), 200


@openapi_route(
    summary="Get survey response detail",
    response_model=SurveyResponseDetailResponses,
    tags=["Survey Responses"],
)
@projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/responses/<uuid:session_id>", methods=["GET"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.submission.view)
def get_response_detail(project_id: int, survey_id: int, session_id: UUID):
    response = build_placeholder_response_detail(survey_id, session_id)
    return response.model_dump(mode="json"), 200


@openapi_route(
    summary="Get survey response history",
    response_model=SurveyResponseHistoryResponses,
    tags=["Survey Responses"],
)
@projects_bp.route(
    "/<bint:project_id>/surveys/<bint:survey_id>/responses/<uuid:session_id>/history", methods=["GET"]
)
@auth.require_auth()
@require_survey_permission(PERMISSIONS.submission.view)
def get_response_history(project_id: int, survey_id: int, session_id: UUID):
    response = build_placeholder_response_history(survey_id, session_id)
    return response.model_dump(mode="json"), 200


@openapi_route(
    summary="Export survey responses",
    request_model=ExportSurveyResponsesRequest,
    response_model=SurveyResponseExportResponses,
    status_code=202,
    tags=["Survey Responses"],
)
@projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/responses/export", methods=["POST"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.submission.view)
def export_responses(project_id: int, survey_id: int):
    payload = parse(ExportSurveyResponsesRequest, request)
    session_count = len(payload.session_ids) if payload.session_ids is not None else 0
    response = build_placeholder_response_export(
        export_format=payload.format,
        include_history=payload.include_history,
        session_count=session_count,
    )
    return response.model_dump(mode="json"), 202


@openapi_route(
    summary="Delete survey response",
    status_code=204,
    tags=["Survey Responses"],
)
@projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/responses/<uuid:session_id>", methods=["DELETE"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.submission.view)
def delete_response(project_id: int, survey_id: int, session_id: UUID):
    return "", 204
