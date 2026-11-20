from sqlalchemy.orm import Session

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
from app.repositories import (
    response_stores_repo as rsr,
)
from app.repositories import (
    surveys_repo as sr,
)
from app.schema.enums import SurveyVisibility
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.user import User
from app.schema.types import ProjectId, ResponseStoreId, Slug, SurveyId, SurveyTitle, SurveyVersionNumber, UserId


class SurveyService:
    """Service for survey and survey version operations."""

    def _ensure_project_default_response_store_id(
        self,
        db: Session,
        *,
        project_id: ProjectId,
        created_by_user_id: UserId | None,
    ) -> ResponseStoreId:
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
        created_by_user_id: UserId | None,
    ) -> ResponseStoreId:
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
    def list_surveys(self, db: Session, *, project_id: ProjectId, actor: User) -> list[Survey]:  # noqa: ARG002
        return sr.list_surveys(db, project_id)

    def create_survey(
        self,
        db: Session,
        *,
        project_id: ProjectId,
        title: SurveyTitle,
        visibility: SurveyVisibility,
        public_slug: Slug | None,
        actor: User,
    ) -> Survey:
        survey_rules.ensure_visibility_slug_coherent(visibility=visibility, public_slug=public_slug)
        default_response_store_id = self._ensure_project_default_response_store_id(
            db,
            project_id=project_id,
            created_by_user_id=actor.id,
        )
        survey = sr.create_survey(
            db,
            project_id,
            title=title,
            visibility=visibility,
            public_slug=public_slug,
            default_response_store_id=default_response_store_id,
            created_by_user_id=actor.id,
        )
        commit_with_err_handle(db, contexts=[survey])
        return survey

    def get_survey(self, db: Session, *, project_id: ProjectId, survey_id: SurveyId, actor: User) -> Survey:  # noqa: ARG002
        return ensure_present(
            sr.get_survey(db, project_id, survey_id),
            error=SurveyNotFoundError(survey_id=survey_id, project_id=project_id),
        )

    def _get_survey(self, db: Session, project_id: ProjectId, survey_id: SurveyId) -> Survey:
        return ensure_present(
            sr.get_survey(db, project_id, survey_id),
            error=SurveyNotFoundError(survey_id=survey_id, project_id=project_id),
        )

    def update_survey(
        self,
        db: Session,
        *,
        project_id: ProjectId,
        survey_id: SurveyId,
        actor: User,  # noqa: ARG002
        title: SurveyTitle | None,
        visibility: SurveyVisibility | None,
        public_slug: Slug | None,
        update_public_slug: bool,
    ) -> Survey:
        survey = self._get_survey(db, project_id, survey_id)
        merged_visibility = visibility if visibility is not None else survey.visibility
        merged_public_slug = public_slug if update_public_slug else survey.public_slug
        survey_rules.ensure_visibility_slug_coherent(
            visibility=merged_visibility,
            public_slug=merged_public_slug,
        )
        updated = sr.update_survey(
            db,
            survey,
            title=title if title is not None else survey.title,
            visibility=merged_visibility,
            public_slug=merged_public_slug,
        )
        commit_with_err_handle(db, contexts=[updated])
        return updated

    def delete_survey(self, db: Session, project_id: ProjectId, survey_id: SurveyId, actor: User) -> None:  # noqa: ARG002
        survey = self._get_survey(db, project_id, survey_id)
        sr.delete_survey(db, survey)
        commit_with_err_handle(db, contexts=[survey])

    # ── Survey versions ───────────────────────────────────────────────────────

    def _get_version(
        self,
        db: Session,
        project_id: ProjectId,
        survey_id: SurveyId,
        version_number: SurveyVersionNumber,
        *,
        for_update: bool = False,
    ) -> SurveyVersion:
        version = ensure_present(
            sr.get_version(db, project_id, survey_id, version_number, for_update=for_update),
            error=VersionNotFoundError(survey_id=survey_id, version_number=version_number),
        )
        return version

    def list_versions(
        self,
        db: Session,
        project_id: ProjectId,
        survey_id: SurveyId,
        actor: User,  # noqa: ARG002
    ) -> list[SurveyVersion]:
        self._get_survey(db, project_id, survey_id)
        return sr.list_versions(db, survey_id)

    def get_version(
        self,
        db: Session,
        project_id: ProjectId,
        survey_id: SurveyId,
        version_number: SurveyVersionNumber,
        actor: User,  # noqa: ARG002
    ) -> SurveyVersion:
        self._get_survey(db, project_id, survey_id)
        return self._get_version(db, project_id, survey_id, version_number)

    def create_version(self, db: Session, project_id: ProjectId, survey_id: SurveyId, actor: User) -> SurveyVersion:
        self._get_survey(db, project_id, survey_id)
        version = sr.create_version(db, survey_id, created_by_user_id=actor.id)
        commit_with_err_handle(db, contexts=[version])
        return version

    def copy_version_to_draft(
        self,
        db: Session,
        project_id: ProjectId,
        survey_id: SurveyId,
        version_number: SurveyVersionNumber,
        actor: User,
    ) -> SurveyVersion:
        self._get_survey(db, project_id, survey_id)
        source_version = self._get_version(db, project_id, survey_id, version_number, for_update=True)

        draft = sr.create_version(
            db,
            survey_id,
            created_by_user_id=actor.id,
            content=source_version.content,
            revision=1 if source_version.content is not None else 0,
        )

        commit_with_err_handle(db, contexts=[draft])
        return draft

    @tracing.action("survey.version.publish")
    def publish_version(
        self,
        db: Session,
        project_id: ProjectId,
        survey_id: SurveyId,
        version_number: SurveyVersionNumber,
        actor: User,
    ) -> SurveyVersion:
        survey = self._get_survey(db, project_id, survey_id)
        version = self._get_version(db, project_id, survey_id, version_number, for_update=True)

        version_rules.ensure_is_draft(version=version)

        version_rules.ensure_publishable(version=version)

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

    def _ensure_survey_encryption_key(
        self,
        db: Session,
        *,
        project_id: ProjectId,
        survey_id: SurveyId,
    ) -> None:
        cache = get_app_cache()
        clients = get_crypto_clients()
        if wrapped_survey_key_exists(db, project_id=project_id, survey_id=survey_id, cache=cache):
            return

        create_wrapped_survey_key(
            db,
            project_id=project_id,
            survey_id=survey_id,
            cache=cache,
            clients=clients,
        )

    def archive_version(
        self,
        db: Session,
        project_id: ProjectId,
        survey_id: SurveyId,
        version_number: SurveyVersionNumber,
        actor: User,  # noqa: ARG002
    ) -> SurveyVersion:
        survey = self._get_survey(db, project_id, survey_id)
        version = self._get_version(db, project_id, survey_id, version_number, for_update=True)
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
