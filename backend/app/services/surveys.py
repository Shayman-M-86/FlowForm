from sqlalchemy.orm import Session  # noqa: I001

from app.core.config import EncryptionSettings
from app.crypto.errors import SurveyBranchKeyUnavailableError
from app.crypto.services import SurveyBranchKeyService
from app.db.error_handling import commit_with_err_handle
from app.domain import survey_rules, version_rules
from app.domain.errors import SurveyNotFoundError, VersionNotFoundError
from app.domain.guards import ensure_present
from app.repositories import (
    content_repo as cr,
    response_stores_repo as rsr,
    surveys_repo as sr,
)
from app.schema.api.requests.surveys import CreateSurveyRequest, UpdateSurveyRequest
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.user import User
from app.services.public_submissions.core.shared.crypto_provider import build_crypto_services


class SurveyService:
    """Service for survey and survey version operations."""

    def __init__(
        self,
        *,
        survey_branch_key_service: SurveyBranchKeyService | None = None,
        encryption_settings: EncryptionSettings | None = None,
    ) -> None:
        self._survey_branch_key_service = survey_branch_key_service
        self._encryption_settings = encryption_settings

    def _ensure_project_default_response_store_id(
        self,
        db: Session,
        *,
        project_id: int,
        created_by_user_id: int | None,
    ) -> int:
        store = rsr.get_or_create_platform_primary_store(
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
    def list_surveys(self, db: Session, *, project_id: int, actor: User) -> list[Survey]:  # noqa: ARG002
        return sr.list_surveys(db, project_id)

    def create_survey(self, db: Session, *, project_id: int, data: CreateSurveyRequest, actor: User) -> Survey:
        default_response_store_id = self._ensure_project_default_response_store_id(
            db,
            project_id=project_id,
            created_by_user_id=actor.id,
        )
        survey = sr.create_survey(
            db,
            project_id,
            data,
            default_response_store_id=default_response_store_id,
            created_by_user_id=actor.id,
        )
        commit_with_err_handle(db, contexts=[survey])
        return survey

    def get_survey(self, db: Session, *, project_id: int, survey_id: int, actor: User) -> Survey:  # noqa: ARG002
        return ensure_present(
            sr.get_survey(db, project_id, survey_id),
            error=SurveyNotFoundError(survey_id=survey_id, project_id=project_id),
        )

    def _get_survey(self, db: Session, project_id: int, survey_id: int) -> Survey:
        return ensure_present(
            sr.get_survey(db, project_id, survey_id),
            error=SurveyNotFoundError(survey_id=survey_id, project_id=project_id),
        )

    def update_survey(
        self,
        db: Session,
        project_id: int,
        survey_id: int,
        data: UpdateSurveyRequest,
        actor: User,  # noqa: ARG002
    ) -> Survey:
        survey = self._get_survey(db, project_id, survey_id)

        changed = data.model_fields_set
        merged_visibility = (
            data.visibility
            if "visibility" in changed and data.visibility is not None
            else survey.visibility
        )
        merged_public_slug = data.public_slug if "public_slug" in changed else survey.public_slug
        survey_rules.ensure_visibility_slug_coherent(
            visibility=merged_visibility,
            public_slug=merged_public_slug,
        )

        updated = sr.update_survey(db, survey, data)
        commit_with_err_handle(db, contexts=[updated])
        return updated

    def delete_survey(self, db: Session, project_id: int, survey_id: int, actor: User) -> None:  # noqa: ARG002
        survey = self._get_survey(db, project_id, survey_id)
        survey_rules.ensure_can_delete_survey(survey)
        sr.delete_survey(db, survey)
        commit_with_err_handle(db, contexts=[survey])

    # ── Survey versions ───────────────────────────────────────────────────────

    def _get_version(self, db: Session, project_id: int, survey_id: int, version_number: int) -> SurveyVersion:
        version = ensure_present(
            sr.get_version(db, project_id, survey_id, version_number),
            error=VersionNotFoundError(survey_id=survey_id, version_number=version_number),
        )
        return version

    def list_versions(self, db: Session, project_id: int, survey_id: int, actor: User) -> list[SurveyVersion]:  # noqa: ARG002
        self._get_survey(db, project_id, survey_id)
        return sr.list_versions(db, survey_id)

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

    def create_version(self, db: Session, project_id: int, survey_id: int, actor: User) -> SurveyVersion:  # noqa: ARG002
        self._get_survey(db, project_id, survey_id)
        version = sr.create_version(db, survey_id)
        commit_with_err_handle(db, contexts=[version])
        return version

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

        draft = sr.create_version(db, survey_id, created_by_user_id=actor.id)
        cr.clone_nodes(db, source_version, draft)
        cr.clone_scoring_rules(db, source_version, draft)

        commit_with_err_handle(db, contexts=[draft])
        return draft

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

        questions = cr.list_nodes(db, version.id)
        version_rules.ensure_has_questions(questions=questions)

        all_nodes = cr.list_nodes(db, version.id)
        scoring_rules = cr.list_scoring_rules(db, version.id)

        compiled = {
            "nodes": [
                {
                    "node_id": str(n.id),
                    "type": n.node_type,
                    "sort_key": n.sort_key,
                    "content": n.question_schema,
                }
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
        self._ensure_survey_encryption_key(
            db,
            project_id=survey.project_id,
            survey_id=survey.id,
        )

        result = sr.publish_version(db, survey, version, compiled)
        commit_with_err_handle(db, contexts=[result, survey, version])
        return result

    def _ensure_survey_encryption_key(
        self,
        db: Session,
        *,
        project_id: int,
        survey_id: int,
    ) -> None:
        self._get_survey_branch_key_service().ensure_for_survey(
            db,
            project_id=project_id,
            survey_id=survey_id,
        )

    def _get_survey_branch_key_service(self) -> SurveyBranchKeyService:
        if self._survey_branch_key_service is None:
            service = build_crypto_services(
                self._encryption_settings
            ).survey_branch_key_service
            if service is None:
                raise SurveyBranchKeyUnavailableError()
            self._survey_branch_key_service = service

        return self._survey_branch_key_service

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
            result = sr.unpublish_version(db, survey, version)
            commit_with_err_handle(db, contexts=[result, version, survey])
            return result

        version_rules.ensure_is_not_active_published(survey=survey, version=version)
        result = sr.archive_version(db, version)
        commit_with_err_handle(db, contexts=[result, version, survey])
        return result
