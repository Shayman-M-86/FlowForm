import csv
import io
import json
from typing import Any
from uuid import UUID

from flask import Response, request

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
    SurveyResponseHistoryResponses,
    SurveyResponseSummaryResponses,
)
from app.services.access.access_service import require_survey_permission
from app.services.admin_responses.service import AdminResponseService

_admin_response_service: AdminResponseService | None = None


def _build_service() -> AdminResponseService:
    global _admin_response_service
    if _admin_response_service is None:
        _admin_response_service = AdminResponseService()
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
    params = parse_query(ListSurveyResponsesRequest, request)
    sessions, total = _build_service().list_responses(
        get_core_db(),
        project_id=project_id,
        survey_id=survey_id,
        status=params.status,
        page=params.page,
        page_size=params.page_size,
    )
    items = [
        SurveyResponseSummaryResponses.model_validate(s, from_attributes=True)
        for s in sessions
    ]
    response = PaginatedSurveyResponsesResponses(
        items=items, total=total, page=params.page, page_size=params.page_size,
    )
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
    status_code=200,
    tags=["Survey Responses"],
)
@studio_projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/responses/export", methods=["POST"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.submission.view)
def export_responses(project_id: int, survey_id: int):
    payload = parse(ExportSurveyResponsesRequest, request)
    results = _build_service().export_responses(
        get_core_db(),
        get_response_db(),
        project_id=project_id,
        survey_id=survey_id,
        session_ids=payload.session_ids,
        include_history=payload.include_history,
    )

    rows = _flatten_export_rows(results, include_history=payload.include_history)

    if payload.format == "json":
        body = json.dumps(rows, default=str, ensure_ascii=False)
        return Response(
            body,
            status=200,
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment; filename=responses_survey_{survey_id}.json"},
        )

    output = io.StringIO()
    fieldnames = [
        "session_id", "status", "started_at", "completed_at",
        "question_key", "answer_family", "answer_state", "answer_value",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

    return Response(
        output.getvalue(),
        status=200,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=responses_survey_{survey_id}.csv"},
    )


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


def _serialize_answer_value(val: Any) -> Any:
    """Serialize answer values for export — Pydantic models to dicts, everything else as-is."""
    if hasattr(val, "model_dump"):
        return val.model_dump(mode="json")
    return val


def _flatten_export_rows(
    results: list[Any],
    *,
    include_history: bool,
) -> list[dict[str, Any]]:
    """Flatten decrypted session results into flat rows for CSV/JSON export."""
    rows: list[dict[str, Any]] = []
    for result in results:
        session = result.session
        answer_list = result.revisions if include_history else result.answers
        if not answer_list:
            row: dict[str, Any] = {
                "session_id": str(session.id),
                "status": session.session_status,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "question_key": None,
                "answer_family": None,
                "answer_state": None,
                "answer_value": None,
            }
            rows.append(row)
            continue

        for answer in answer_list:
            row = {
                "session_id": str(session.id),
                "status": session.session_status,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "question_key": answer.question_key,
                "answer_family": answer.answer_family,
                "answer_state": answer.answer_state,
                "answer_value": _serialize_answer_value(answer.answer_value),
            }
            rows.append(row)
    return rows
