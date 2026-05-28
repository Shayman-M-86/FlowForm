from app.api.v1.projects import projects_bp, survey_service, users_service
from app.core.extensions import auth
from app.db.context import get_core_db
from app.openapi import openapi_route
from app.schema.api.responses.surveys import SurveyVersionOut
from app.schema.orm.core.user import User


@openapi_route(summary="List survey versions", response_model=list[SurveyVersionOut], tags=["Survey Versions"])
@projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/versions", methods=["GET"])
@auth.require_auth()
def list_versions(project_id: int, survey_id: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    versions = survey_service.list_versions(db=db, project_id=project_id, survey_id=survey_id, actor=user)
    return [SurveyVersionOut.model_validate(v).model_dump(mode="json") for v in versions], 200


@openapi_route(
    summary="Create survey version",
    response_model=SurveyVersionOut,
    status_code=201,
    tags=["Survey Versions"],
)
@projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/versions", methods=["POST"])
@auth.require_auth()
def create_version(project_id: int, survey_id: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    version = survey_service.create_version(db=db, project_id=project_id, survey_id=survey_id, actor=user)
    return SurveyVersionOut.model_validate(version).model_dump(mode="json"), 201


@openapi_route(
    summary="Copy survey version to draft",
    response_model=SurveyVersionOut,
    status_code=201,
    tags=["Survey Versions"],
)
@projects_bp.route(
    "/<bint:project_id>/surveys/<bint:survey_id>/versions/<bint:version_number>/copy-to-draft",
    methods=["POST"],
)
@auth.require_auth()
def copy_version_to_draft(project_id: int, survey_id: int, version_number: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    version = survey_service.copy_version_to_draft(
        db=db,
        project_id=project_id,
        survey_id=survey_id,
        version_number=version_number,
        actor=user,
    )
    return SurveyVersionOut.model_validate(version).model_dump(mode="json"), 201


@openapi_route(summary="Get survey version", response_model=SurveyVersionOut, tags=["Survey Versions"])
@projects_bp.route("/<bint:project_id>/surveys/<bint:survey_id>/versions/<bint:version_number>", methods=["GET"])
@auth.require_auth()
def get_version(project_id: int, survey_id: int, version_number: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    version = survey_service.get_version(
        db=db, project_id=project_id, survey_id=survey_id, version_number=version_number, actor=user
    )
    return SurveyVersionOut.model_validate(version).model_dump(mode="json"), 200


@openapi_route(summary="Publish survey version", response_model=SurveyVersionOut, tags=["Survey Versions"])
@projects_bp.route(
    "/<bint:project_id>/surveys/<bint:survey_id>/versions/<bint:version_number>/publish",
    methods=["POST"],
)
@auth.require_auth()
def publish_version(project_id: int, survey_id: int, version_number: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    version = survey_service.publish_version(
        db=db, project_id=project_id, survey_id=survey_id, version_number=version_number, actor=user
    )
    return SurveyVersionOut.model_validate(version).model_dump(mode="json"), 200


@openapi_route(summary="Archive survey version", response_model=SurveyVersionOut, tags=["Survey Versions"])
@projects_bp.route(
    "/<bint:project_id>/surveys/<bint:survey_id>/versions/<bint:version_number>/archive",
    methods=["POST"],
)
@auth.require_auth()
def archive_version(project_id: int, survey_id: int, version_number: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    version = survey_service.archive_version(
        db=db, project_id=project_id, survey_id=survey_id, version_number=version_number, actor=user
    )
    return SurveyVersionOut.model_validate(version).model_dump(mode="json"), 200
