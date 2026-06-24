from uuid import UUID

from flask import request

from app.api.utils.validation import parse, parse_query
from app.api.v1.studio.projects import studio_projects_bp, subject_service
from app.core.extensions import auth
from app.db.context import get_core_db
from app.domain.permissions import PERMISSIONS
from app.openapi import openapi_route
from app.schema.api.requests.subjects import ListSubjectsQuery, UpdateSubjectRequest
from app.schema.api.responses.subjects import (
    ListSubjectsResponse,
    SubjectDetailResponse,
    SubjectResponse,
)
from app.services.access.access_service import require_project_permission

_BASE = "/<bint:project_id>/subjects"


@openapi_route(
    summary="List subjects",
    query_model=ListSubjectsQuery,
    response_model=ListSubjectsResponse,
    tags=["Subjects"],
)
@studio_projects_bp.route(_BASE, methods=["GET"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_members)
def list_subjects(project_id: int):
    params = parse_query(ListSubjectsQuery, request)
    offset = (params.page - 1) * params.page_size
    rows, total = subject_service.list_subjects(
        db=get_core_db(),
        project_id=project_id,
        canonical_status=params.canonical_status,
        is_participant=params.is_participant,
        search=params.search,
        offset=offset,
        limit=params.page_size,
    )
    return ListSubjectsResponse(
        subjects=[SubjectResponse.model_validate(row) for row in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
    ).model_dump(mode="json"), 200


@openapi_route(summary="Get subject", response_model=SubjectDetailResponse, tags=["Subjects"])
@studio_projects_bp.route(f"{_BASE}/<uuid:subject_id>", methods=["GET"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_members)
def get_subject(project_id: int, subject_id: UUID):
    result = subject_service.get_subject(db=get_core_db(), project_id=project_id, subject_id=subject_id)
    return SubjectDetailResponse.model_validate(result).model_dump(mode="json"), 200


@openapi_route(
    summary="Update subject",
    request_model=UpdateSubjectRequest,
    response_model=SubjectDetailResponse,
    tags=["Subjects"],
)
@studio_projects_bp.route(f"{_BASE}/<uuid:subject_id>", methods=["PATCH"])
@auth.require_auth()
@require_project_permission(PERMISSIONS.project.manage_members)
def update_subject(project_id: int, subject_id: UUID):
    payload = parse(UpdateSubjectRequest, request)
    result = subject_service.update_subject(
        db=get_core_db(), project_id=project_id, subject_id=subject_id, data=payload
    )
    return SubjectDetailResponse.model_validate(result).model_dump(mode="json"), 200
