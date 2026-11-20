from flask import g, request

from app.api.utils.validation import parse
from app.api.v1.studio.projects import content_svc, studio_projects_bp, survey_service
from app.core.extensions import auth
from app.db.context import get_core_db
from app.domain.permissions import PERMISSIONS
from app.openapi import openapi_route
from app.schema.api.requests.surveys import SaveSurveyRequest
from app.schema.api.responses.surveys import (
    ArchiveSurveyResponse,
    CopySurveyVersionResponse,
    CreateSurveyVersionResponse,
    GetSurveyVersionResponse,
    PublishSurveyResponse,
    SaveSurveyResponse,
    SurveyVersionListItemResponse,
)
from app.schema.types import ProjectId, SurveyId, SurveyVersionId, SurveyVersionNumber
from app.services.access.access_service import require_survey_permission


@openapi_route(
    summary="List survey versions", response_model=list[SurveyVersionListItemResponse], tags=["Survey Versions"]
)
@studio_projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/versions", methods=["GET"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.view)
def list_versions(project_id: ProjectId, survey_id: SurveyId):
    versions = survey_service.list_versions(db=get_core_db(), project_id=project_id, survey_id=survey_id, actor=g.actor)
    return [
        SurveyVersionListItemResponse(
            version_id=version.id,
            version_number=version.version_number,
            revision=version.revision,
            status=version.status,
            published_at=version.published_at,
            created_at=version.created_at,
            updated_at=version.updated_at,
        ).model_dump(mode="json")
        for version in versions
    ], 200


@openapi_route(
    summary="Create survey version",
    response_model=CreateSurveyVersionResponse,
    status_code=201,
    tags=["Survey Versions"],
)
@studio_projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/versions", methods=["POST"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.create)
def create_version(project_id: ProjectId, survey_id: SurveyId):
    version = survey_service.create_version(db=get_core_db(), project_id=project_id, survey_id=survey_id, actor=g.actor)
    return CreateSurveyVersionResponse(
        version_id=version.id, version_number=version.version_number, revision=version.revision
    ).model_dump(mode="json"), 201


@openapi_route(
    summary="Copy survey version to draft",
    response_model=CopySurveyVersionResponse,
    status_code=201,
    tags=["Survey Versions"],
)
@studio_projects_bp.route(
    "/<bint:project_id>/surveys/<bint:survey_id>/versions/<bint:version_number>/copy-to-draft",
    methods=["POST"],
)
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.create)
def copy_version_to_draft(project_id: ProjectId, survey_id: SurveyId, version_number: SurveyVersionNumber):
    version = survey_service.copy_version_to_draft(
        db=get_core_db(),
        project_id=project_id,
        survey_id=survey_id,
        version_number=version_number,
        actor=g.actor,
    )
    return CopySurveyVersionResponse(
        version_id=version.id, version_number=version.version_number, revision=version.revision
    ).model_dump(mode="json"), 201


@openapi_route(summary="Get survey version", response_model=GetSurveyVersionResponse, tags=["Survey Versions"])
@studio_projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/versions/<bint:version_number>", methods=["GET"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.view)
def get_version(project_id: ProjectId, survey_id: SurveyId, version_number: SurveyVersionNumber):
    version = survey_service.get_version(
        db=get_core_db(), project_id=project_id, survey_id=survey_id, version_number=version_number, actor=g.actor
    )
    return GetSurveyVersionResponse(
        version_id=version.id, revision=version.revision, status=version.status, content=version.content
    ).model_dump(mode="json"), 200


@openapi_route(summary="Publish survey version", response_model=PublishSurveyResponse, tags=["Survey Versions"])
@studio_projects_bp.route(
    "/<bint:project_id>/surveys/<bint:survey_id>/versions/<bint:version_number>/publish",
    methods=["POST"],
)
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.publish)
def publish_version(project_id: ProjectId, survey_id: SurveyId, version_number: SurveyVersionNumber):
    version = survey_service.publish_version(
        db=get_core_db(), project_id=project_id, survey_id=survey_id, version_number=version_number, actor=g.actor
    )
    return PublishSurveyResponse(version_id=version.id, status=version.status).model_dump(mode="json"), 200


@openapi_route(summary="Archive survey version", response_model=ArchiveSurveyResponse, tags=["Survey Versions"])
@studio_projects_bp.route(
    "/<bint:project_id>/surveys/<bint:survey_id>/versions/<bint:version_number>/archive",
    methods=["POST"],
)
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.archive)
def archive_version(project_id: ProjectId, survey_id: SurveyId, version_number: SurveyVersionNumber):
    version = survey_service.archive_version(
        db=get_core_db(), project_id=project_id, survey_id=survey_id, version_number=version_number, actor=g.actor
    )
    return ArchiveSurveyResponse(version_id=version.id, status=version.status).model_dump(mode="json"), 200


@openapi_route(
    summary="Save survey content",
    request_model=SaveSurveyRequest,
    response_model=SaveSurveyResponse,
    tags=["Survey Versions"],
)
@studio_projects_bp.route(
    "/<bint:project_id>/surveys/<bint:survey_id>/versions/<bint:version_id>/content",
    methods=["PUT"],
)
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.edit)
def save_survey_content(project_id: ProjectId, survey_id: SurveyId, version_id: SurveyVersionId):
    payload = parse(SaveSurveyRequest, request)
    revision = content_svc.save_content(
        get_core_db(),
        project_id=project_id,
        survey_id=survey_id,
        version_id=version_id,
        expected_revision=payload.expected_revision,
        content=payload.content,
    )
    return SaveSurveyResponse(revision=revision).model_dump(mode="json"), 200
