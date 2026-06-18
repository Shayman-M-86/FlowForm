from flask import g

from app.api.v1.studio.projects import studio_projects_bp, survey_service
from app.core.extensions import auth
from app.db.context import get_core_db
from app.domain.permissions import PERMISSIONS
from app.openapi import openapi_route
from app.schema.api.responses.surveys import SurveyVersionResponses
from app.services.access.access_service import require_survey_permission


@openapi_route(summary="List survey versions", response_model=list[SurveyVersionResponses], tags=["Survey Versions"])
@studio_projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/versions", methods=["GET"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.view)
def list_versions(project_id: int, survey_id: int):
    versions = survey_service.list_versions(db=get_core_db(), project_id=project_id, survey_id=survey_id, actor=g.actor)
    return [SurveyVersionResponses.model_validate(v).model_dump(mode="json") for v in versions], 200


@openapi_route(
    summary="Create survey version",
    response_model=SurveyVersionResponses,
    status_code=201,
    tags=["Survey Versions"],
)
@studio_projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/versions", methods=["POST"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.create)
def create_version(project_id: int, survey_id: int):
    version = survey_service.create_version(db=get_core_db(), project_id=project_id, survey_id=survey_id, actor=g.actor)
    return SurveyVersionResponses.model_validate(version).model_dump(mode="json"), 201


@openapi_route(
    summary="Copy survey version to draft",
    response_model=SurveyVersionResponses,
    status_code=201,
    tags=["Survey Versions"],
)
@studio_projects_bp.route(
    "/<bint:project_id>/surveys/<bint:survey_id>/versions/<bint:version_number>/copy-to-draft",
    methods=["POST"],
)
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.create)
def copy_version_to_draft(project_id: int, survey_id: int, version_number: int):
    version = survey_service.copy_version_to_draft(
        db=get_core_db(),
        project_id=project_id,
        survey_id=survey_id,
        version_number=version_number,
        actor=g.actor,
    )
    return SurveyVersionResponses.model_validate(version).model_dump(mode="json"), 201


@openapi_route(summary="Get survey version", response_model=SurveyVersionResponses, tags=["Survey Versions"])
@studio_projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/versions/<bint:version_number>", methods=["GET"])
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.view)
def get_version(project_id: int, survey_id: int, version_number: int):
    version = survey_service.get_version(
        db=get_core_db(), project_id=project_id, survey_id=survey_id, version_number=version_number, actor=g.actor
    )
    return SurveyVersionResponses.model_validate(version).model_dump(mode="json"), 200


@openapi_route(summary="Publish survey version", response_model=SurveyVersionResponses, tags=["Survey Versions"])
@studio_projects_bp.route(
    "/<bint:project_id>/surveys/<bint:survey_id>/versions/<bint:version_number>/publish",
    methods=["POST"],
)
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.publish)
def publish_version(project_id: int, survey_id: int, version_number: int):
    version = survey_service.publish_version(
        db=get_core_db(), project_id=project_id, survey_id=survey_id, version_number=version_number, actor=g.actor
    )
    return SurveyVersionResponses.model_validate(version).model_dump(mode="json"), 200


@openapi_route(summary="Archive survey version", response_model=SurveyVersionResponses, tags=["Survey Versions"])
@studio_projects_bp.route(
    "/<bint:project_id>/surveys/<bint:survey_id>/versions/<bint:version_number>/archive",
    methods=["POST"],
)
@auth.require_auth()
@require_survey_permission(PERMISSIONS.survey.archive)
def archive_version(project_id: int, survey_id: int, version_number: int):
    version = survey_service.archive_version(
        db=get_core_db(), project_id=project_id, survey_id=survey_id, version_number=version_number, actor=g.actor
    )
    return SurveyVersionResponses.model_validate(version).model_dump(mode="json"), 200
