from app.api.v1.projects import projects_bp, survey_service, users_service
from app.api.v1.projects.resolver import resolve_project_ref
from app.core.extensions import auth
from app.db.context import get_core_db
from app.schema.api.responses.surveys import SurveyVersionOut
from app.schema.orm.core.user import User


@projects_bp.route("/<project_ref>/surveys/<int:survey_id>/versions", methods=["GET"])
@auth.require_auth()
def list_versions(project_ref: str, survey_id: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    versions = survey_service.list_versions(db=db, project_id=project_id, survey_id=survey_id, actor=user)
    return [SurveyVersionOut.model_validate(v).model_dump(mode="json") for v in versions], 200


@projects_bp.route("/<project_ref>/surveys/<int:survey_id>/versions", methods=["POST"])
@auth.require_auth()
def create_version(project_ref: str, survey_id: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    version = survey_service.create_version(db=db, project_id=project_id, survey_id=survey_id, actor=user)
    return SurveyVersionOut.model_validate(version).model_dump(mode="json"), 201


@projects_bp.route("/<project_ref>/surveys/<int:survey_id>/versions/<int:version_number>", methods=["GET"])
@auth.require_auth()
def get_version(project_ref: str, survey_id: int, version_number: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    version = survey_service.get_version(
        db=db, project_id=project_id, survey_id=survey_id, version_number=version_number, actor=user
    )
    return SurveyVersionOut.model_validate(version).model_dump(mode="json"), 200


@projects_bp.route(
    "/<project_ref>/surveys/<int:survey_id>/versions/<int:version_number>/publish",
    methods=["POST"],
)
@auth.require_auth()
def publish_version(project_ref: str, survey_id: int, version_number: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    version = survey_service.publish_version(
        db=db, project_id=project_id, survey_id=survey_id, version_number=version_number, actor=user
    )
    return SurveyVersionOut.model_validate(version).model_dump(mode="json"), 200


@projects_bp.route(
    "/<project_ref>/surveys/<int:survey_id>/versions/<int:version_number>/archive",
    methods=["POST"],
)
@auth.require_auth()
def archive_version(project_ref: str, survey_id: int, version_number: int):
    db = get_core_db()
    user: User = users_service.get_user_by_sub(db=db, auth0_user_id=auth.get_current_user_sub())
    project_id = resolve_project_ref(db, project_ref, user).id
    version = survey_service.archive_version(
        db=db, project_id=project_id, survey_id=survey_id, version_number=version_number, actor=user
    )
    return SurveyVersionOut.model_validate(version).model_dump(mode="json"), 200
