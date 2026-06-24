from uuid import UUID

from flask import request

from app.api.utils.validation import parse, parse_query
from app.api.v1.studio.projects import studio_projects_bp
from app.core.extensions import auth
from app.db.context import get_core_db, get_response_db
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
from app.services.admin_responses.service import AdminResponseService
from app.services.public_submissions.core.shared.crypto_provider import get_crypto_services

_admin_response_service: AdminResponseService | None = None


def _build_service() -> AdminResponseService:
    global _admin_response_service
    if _admin_response_service is None:
        _admin_response_service = AdminResponseService(get_crypto_services())
    return _admin_response_service


@openapi_route(
    summary="List survey responses",
    query_model=ListSurveyResponsesRequest,
    response_model=PaginatedSurveyResponsesResponses,
    tags=["Survey Responses"],
)
@studio_projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/responses", methods=["GET"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.submission.view)
def list_responses(project_id: int, survey_id: int):
    _ = project_id, survey_id
    params = parse_query(ListSurveyResponsesRequest, request)
    response = PaginatedSurveyResponsesResponses(items=[], total=0, page=params.page, page_size=params.page_size)
    return response.model_dump(mode="json"), 200


@openapi_route(
    summary="Get survey response detail",
    response_model=SurveyResponseDetailResponses,
    tags=["Survey Responses"],
)
@studio_projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/responses/<uuid:session_id>", methods=["GET"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.submission.view)
def get_response_detail(project_id: int, survey_id: int, session_id: UUID):
    _ = project_id
    result = _build_service().get_session_detail(
        get_core_db(), get_response_db(), survey_id=survey_id, session_id=session_id,
    )
    return SurveyResponseDetailResponses.model_validate(result, from_attributes=True).model_dump(mode="json"), 200


@openapi_route(
    summary="Get survey response history",
    response_model=SurveyResponseHistoryResponses,
    tags=["Survey Responses"],
)
@studio_projects_bp.route(
    "/<bint:project_id>/surveys/<bint:survey_id>/responses/<uuid:session_id>/history", methods=["GET"]
)
@auth.require_auth()
@require_survey_permission(PERMISSIONS.submission.view)
def get_response_history(project_id: int, survey_id: int, session_id: UUID):
    _ = project_id
    result = _build_service().get_session_history(
        get_core_db(), get_response_db(), survey_id=survey_id, session_id=session_id,
    )
    return SurveyResponseHistoryResponses.model_validate(result, from_attributes=True).model_dump(mode="json"), 200


@openapi_route(
    summary="Export survey responses",
    request_model=ExportSurveyResponsesRequest,
    response_model=SurveyResponseExportResponses,
    status_code=202,
    tags=["Survey Responses"],
)
@studio_projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/responses/export", methods=["POST"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.submission.view)
def export_responses(project_id: int, survey_id: int):
    _ = project_id, survey_id
    payload = parse(ExportSurveyResponsesRequest, request)
    session_count = len(payload.session_ids) if payload.session_ids is not None else 0
    response = SurveyResponseExportResponses(
        format="json" if payload.format == "json" else "csv",
        include_history=payload.include_history,
        session_count=session_count,
        download_url=None,
    )
    return response.model_dump(mode="json"), 202


@openapi_route(
    summary="Delete survey response",
    status_code=204,
    tags=["Survey Responses"],
)
@studio_projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/responses/<uuid:session_id>", methods=["DELETE"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.submission.view)
def delete_response(project_id: int, survey_id: int, session_id: UUID):
    _ = project_id
    _build_service().delete_session(
        get_core_db(), get_response_db(), survey_id=survey_id, session_id=session_id,
    )
    return "", 204
