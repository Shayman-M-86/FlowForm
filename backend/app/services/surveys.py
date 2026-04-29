from sqlalchemy.orm import Session

from app.db.error_handling import commit_with_err_handle
from app.domain import survey_rules, version_rules
from app.domain.permissions import PERMISSIONS
from app.repositories import content_repo, response_stores_repo, surveys_repo
from app.schema.api.requests.surveys import CreateSurveyRequest, UpdateSurveyRequest
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.user import User
from app.services.access.access_service import require_project_permission, require_survey_permission


class SurveyService:
    """Service for survey and survey version operations."""

    def _ensure_project_default_response_store_id(
        self,
        db: Session,
        *,
        project_id: int,
        created_by_user_id: int | None,
    ) -> int:
        store = response_stores_repo.get_or_create_platform_primary_store(
            db,
            project_id,
            created_by_user_id=created_by_user_id,
        )
        return store.id

    def _ensure_survey_default_response_store(
        self,
        db: Session,
        *,
        survey: Survey,
        created_by_user_id: int | None,
    ) -> int:
        default_response_store_id = self._ensure_project_default_response_store_id(
            db,
            project_id=survey.project_id,
            created_by_user_id=created_by_user_id,
        )
        return survey_rules.ensure_default_response_store(
            survey=survey,
            default_response_store_id=default_response_store_id,
        )

    # ── Surveys ───────────────────────────────────────────────────────────────
    @require_project_permission(PERMISSIONS.survey.view)
    def list_surveys(self, db: Session, *, project_id: int, actor: User) -> list[Survey]:  # noqa: ARG002
        return surveys_repo.list_surveys(db, project_id)

    @require_project_permission(PERMISSIONS.survey.create)
    def create_survey(self, db: Session, *, project_id: int, data: CreateSurveyRequest, actor: User) -> Survey:

        if data.default_response_store_id is None:
            data = data.model_copy(
                update={
                    "default_response_store_id": self._ensure_project_default_response_store_id(
                        db,
                        project_id=project_id,
                        created_by_user_id=actor.id,
                    )
                }
            )
        survey = surveys_repo.create_survey(db, project_id, data)
        commit_with_err_handle(db, contexts=[survey])
        return survey

    @require_survey_permission(PERMISSIONS.survey.view)
    def get_survey(self, db: Session, *, project_id: int, survey_id: int, actor: User) -> Survey:  # noqa: ARG002
        return survey_rules.ensure_not_none(
            survey=surveys_repo.get_survey(db, project_id, survey_id),
            survey_id=survey_id,
            project_id=project_id,
        )

    def _get_survey(self, db: Session, project_id: int, survey_id: int) -> Survey:
        return survey_rules.ensure_not_none(
            survey=surveys_repo.get_survey(db, project_id, survey_id),
            survey_id=survey_id,
            project_id=project_id,
        )

    @require_survey_permission(PERMISSIONS.survey.edit)
    def update_survey(
        self,
        db: Session,
        project_id: int,
        survey_id: int,
        data: UpdateSurveyRequest,
        actor: User,  # noqa: ARG002
    ) -> Survey:
        survey = self._get_survey(db, project_id, survey_id)

        updated = surveys_repo.update_survey(db, survey, data)
        commit_with_err_handle(db, contexts=[updated])
        return updated

    @require_survey_permission(PERMISSIONS.survey.delete)
    def delete_survey(self, db: Session, project_id: int, survey_id: int, actor: User) -> None:  # noqa: ARG002
        survey = self._get_survey(db, project_id, survey_id)
        survey_rules.ensure_can_delete_survey(survey)
        surveys_repo.delete_survey(db, survey)
        commit_with_err_handle(db, contexts=[survey])

    # ── Survey versions ───────────────────────────────────────────────────────

    def _get_version(self, db: Session, project_id: int, survey_id: int, version_number: int) -> SurveyVersion:
        version = version_rules.ensure_not_none(
            version=surveys_repo.get_version(db, project_id, survey_id, version_number),
            version_number=version_number,
            survey_id=survey_id,
        )
        return version

    @require_survey_permission(PERMISSIONS.survey.view)
    def list_versions(self, db: Session, project_id: int, survey_id: int, actor: User) -> list[SurveyVersion]:  # noqa: ARG002
        self._get_survey(db, project_id, survey_id)
        return surveys_repo.list_versions(db, survey_id)

    @require_survey_permission(PERMISSIONS.survey.view)
    def get_version(
        self,
        db: Session,
        project_id: int,
        survey_id: int,
        version_number: int,
        actor: User,  # noqa: ARG002
    ) -> SurveyVersion:
        self._get_survey(db, project_id, survey_id)
        return self._get_version(db, project_id, survey_id, version_number)

    @require_survey_permission(PERMISSIONS.survey.create)
    def create_version(self, db: Session, project_id: int, survey_id: int, actor: User) -> SurveyVersion:  # noqa: ARG002
        self._get_survey(db, project_id, survey_id)
        version = surveys_repo.create_version(db, survey_id)
        commit_with_err_handle(db, contexts=[version])
        return version

    @require_survey_permission(PERMISSIONS.survey.create)
    def copy_version_to_draft(
        self,
        db: Session,
        project_id: int,
        survey_id: int,
        version_number: int,
        actor: User,
    ) -> SurveyVersion:
        self._get_survey(db, project_id, survey_id)
        source_version = self._get_version(db, project_id, survey_id, version_number)

        draft = surveys_repo.create_version(db, survey_id, created_by_user_id=actor.id)
        content_repo.clone_questions(db, source_version, draft)
        content_repo.clone_rules(db, source_version, draft)
        content_repo.clone_scoring_rules(db, source_version, draft)

        commit_with_err_handle(db, contexts=[draft])
        return draft

    @require_survey_permission(PERMISSIONS.survey.publish)
    def publish_version(
        self,
        db: Session,
        project_id: int,
        survey_id: int,
        version_number: int,
        actor: User,
    ) -> SurveyVersion:
        survey = self._get_survey(db, project_id, survey_id)
        version = self._get_version(db, project_id, survey_id, version_number)

        version_rules.ensure_is_draft(version=version)

        questions = content_repo.list_questions(db, version.id)
        version_rules.ensure_has_questions(questions=questions)

        all_nodes = content_repo.list_nodes(db, version.id)
        scoring_rules = content_repo.list_scoring_rules(db, version.id)

        compiled = {
            "nodes": [
                {"type": n.node_type, "sort_key": n.sort_key, "content": n.question_schema}
                for n in all_nodes
            ],
            "scoring_rules": [
                {"id": s.id, "scoring_key": s.scoring_key, "scoring_schema": s.scoring_schema} for s in scoring_rules
            ],
        }
        self._ensure_survey_default_response_store(
            db,
            survey=survey,
            created_by_user_id=actor.id,
        )

        result = surveys_repo.publish_version(db, survey, version, compiled)
        commit_with_err_handle(db, contexts=[result, survey, version])
        return result

    @require_survey_permission(PERMISSIONS.survey.archive)
    def archive_version(
        self,
        db: Session,
        project_id: int,
        survey_id: int,
        version_number: int,
        actor: User,  # noqa: ARG002
    ) -> SurveyVersion:
        survey = self._get_survey(db, project_id, survey_id)
        version = self._get_version(db, project_id, survey_id, version_number)
        version_rules.ensure_can_archive(version=version)
        if survey.published_version_id == version.id:
            version_rules.ensure_is_published(version=version)
            result = surveys_repo.unpublish_version(db, survey, version)
            commit_with_err_handle(db, contexts=[result, version, survey])
            return result

        version_rules.ensure_is_not_active_published(survey=survey, version=version)
        result = surveys_repo.archive_version(db, version)
        commit_with_err_handle(db, contexts=[result, version, survey])
        return result
