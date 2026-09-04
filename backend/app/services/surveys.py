from sqlalchemy.orm import Session  # noqa: I001

from app import tracing
from app.cache import get_app_cache
from app.crypto._internal.client_extension import get_crypto_clients
from app.crypto.survey_key import (
    create_wrapped_survey_key,
    wrapped_survey_key_exists,
)
from app.db.error_handling import commit_with_err_handle
from app.domain import survey_rules, version_rules
from app.domain.errors import SurveyNotFoundError, VersionNotFoundError
from app.domain.guards import ensure_present
from app.domain.surveys.publication import ensure_publishable
from app.repositories import (
    response_stores_repo as rsr,
    surveys_repo as sr,
)
from app.schema.api.content.survey_document import SurveyDefinition
from app.schema.api.requests.surveys import CreateSurveyRequest, UpdateSurveyRequest
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.user import User


class SurveyService:
    """Service for survey and survey version operations."""

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

    def create_version(
        self,
        db: Session,
        project_id: int,
        survey_id: int,
        definition: SurveyDefinition,
        actor: User,
    ) -> SurveyVersion:
        self._get_survey(db, project_id, survey_id)
        version = sr.create_version(
            db,
            survey_id,
            definition.model_dump(by_alias=True, mode="json"),
            created_by_user_id=actor.id,
        )
        commit_with_err_handle(db, contexts=[version])
        return version

    def load_definition(
        self,
        db: Session,
        project_id: int,
        survey_id: int,
        version_number: int,
        actor: User,  # noqa: ARG002
    ) -> SurveyDefinition:
        version = self._get_version(db, project_id, survey_id, version_number)
        return self._definition_from_version(version)

    def replace_definition(
        self,
        db: Session,
        project_id: int,
        survey_id: int,
        version_number: int,
        definition: SurveyDefinition,
        actor: User,  # noqa: ARG002
    ) -> SurveyVersion:
        version = self._get_version(db, project_id, survey_id, version_number)
        version_rules.ensure_is_editable(version=version)
        result = sr.replace_definition(
            db,
            version,
            definition.model_dump(by_alias=True, mode="json"),
        )
        commit_with_err_handle(db, contexts=[result])
        return result

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

        definition = self._definition_from_version(source_version)
        draft = sr.create_version(
            db,
            survey_id,
            definition.model_dump(by_alias=True, mode="json"),
            created_by_user_id=actor.id,
        )

        commit_with_err_handle(db, contexts=[draft])
        return draft

    @tracing.action("survey.version.publish")
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
        definition = self._definition_from_version(version)
        ensure_publishable(definition)
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

        result = sr.publish_version(db, survey, version)
        commit_with_err_handle(db, contexts=[result, survey, version])
        tracing.fields(outcome="published", version_number=version_number)
        return result

    @staticmethod
    def _definition_from_version(version: SurveyVersion) -> SurveyDefinition:
        """Parse the persisted JSON at the service boundary before use."""
        return SurveyDefinition.model_validate(version.definition)

    def _ensure_survey_encryption_key(
        self,
        db: Session,
        *,
        project_id: int,
        survey_id: int,
    ) -> None:
        cache = get_app_cache()
        clients = get_crypto_clients()
        if wrapped_survey_key_exists(db, project_id=project_id, survey_id=survey_id, cache=cache):
            return

        create_wrapped_survey_key(
            db, project_id=project_id, survey_id=survey_id, cache=cache, clients=clients,
        )

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
