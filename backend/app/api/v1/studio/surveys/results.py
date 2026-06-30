from uuid import UUID

from flask import Response, request

from app.api.utils.validation import parse, parse_query
from app.api.v1.studio.projects import studio_projects_bp
from app.core.extensions import auth
from app.db.context import get_core_db, get_response_db
from app.domain.permissions import PERMISSIONS
from app.openapi import openapi_route
from app.schema.api.requests.survey_results import (
    ExportSurveyResultsRequest,
    GetSubjectTreeRequest,
    ListSubjectsRequest,
)
from app.schema.api.responses.survey_results import (
    PaginatedSurveySubjectTreesResponses,
    SurveySubjectTreeResponses,
)
from app.services.access.access_service import require_survey_permission
from app.services.admin_results.service import AdminResultsService

_admin_results_service: AdminResultsService | None = None


def _build_service() -> AdminResultsService:
    global _admin_results_service
    if _admin_results_service is None:
        _admin_results_service = AdminResultsService()
    return _admin_results_service


@openapi_route(
    summary="List survey result subjects",
    query_model=ListSubjectsRequest,
    response_model=PaginatedSurveySubjectTreesResponses,
    tags=["Survey Results"],
)
@studio_projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/results/subjects", methods=["GET"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.submission.view)
def list_survey_result_subjects(project_id: int, survey_id: int):
    params = parse_query(ListSubjectsRequest, request)
    items, total = _build_service().list_subjects(
        get_core_db(),
        get_response_db(),
        project_id=project_id,
        survey_id=survey_id,
        page=params.page,
        page_size=params.page_size,
        include_decrypted_answer_values=params.include_decrypted_answer_values,
        include_events=params.include_events,
    )
    response = PaginatedSurveySubjectTreesResponses.model_validate(
        {
            "items": items,
            "total": total,
            "page": params.page,
            "page_size": params.page_size,
            "include_decrypted_answer_values": params.include_decrypted_answer_values,
        },
        from_attributes=True,
    )
    return response.model_dump(mode="json"), 200


@openapi_route(
    summary="Get survey result subject tree",
    query_model=GetSubjectTreeRequest,
    response_model=SurveySubjectTreeResponses,
    tags=["Survey Results"],
)
@studio_projects_bp.route(
    "/<bint:project_id>/surveys/<bint:survey_id>/results/subjects/<uuid:subject_id>", methods=["GET"]
)
@auth.require_auth()
@require_survey_permission(PERMISSIONS.submission.view)
def get_subject_tree(project_id: int, survey_id: int, subject_id: UUID):
    params = parse_query(GetSubjectTreeRequest, request)
    result = _build_service().get_subject_tree(
        get_core_db(),
        get_response_db(),
        project_id=project_id,
        survey_id=survey_id,
        subject_id=subject_id,
        include_decrypted_answer_values=params.include_decrypted_answer_values,
        include_events=params.include_events,
    )
    return SurveySubjectTreeResponses.model_validate(result, from_attributes=True).model_dump(mode="json"), 200


@openapi_route(
    summary="Export survey results",
    description=(
        "Streams a CSV or JSON file attachment (one row per answer slot), not a JSON envelope. "
        "Use the `format` field on the request body to choose CSV or JSON."
    ),
    request_model=ExportSurveyResultsRequest,
    status_code=200,
    tags=["Survey Results"],
)
@studio_projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/results/export", methods=["POST"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.submission.view)
def export_results(project_id: int, survey_id: int):
    payload = parse(ExportSurveyResultsRequest, request)
    export_file = _build_service().export_results(
        get_core_db(),
        get_response_db(),
        project_id=project_id,
        survey_id=survey_id,
        export_format=payload.format,
        session_ids=payload.session_ids,
        include_decrypted_answer_values=payload.include_decrypted_answer_values,
    )
    return Response(
        export_file.body,
        status=200,
        mimetype=export_file.mimetype,
        headers={"Content-Disposition": f"attachment; filename={export_file.filename}"},
    )


@openapi_route(
    summary="Delete survey response session",
    status_code=204,
    tags=["Survey Results"],
)
@studio_projects_bp.route(
    "/<bint:project_id>/surveys/<bint:survey_id>/results/sessions/<uuid:session_id>", methods=["DELETE"]
)
@auth.require_auth()
@require_survey_permission(PERMISSIONS.submission.view)
def delete_session(project_id: int, survey_id: int, session_id: UUID):
    _ = project_id
    _build_service().delete_session(
        get_core_db(),
        get_response_db(),
        survey_id=survey_id,
        session_id=session_id,
    )
    return "", 204
