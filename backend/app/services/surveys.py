from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.transaction import commit_or_rollback
from app.domain import survey_rules, version_rules
from app.domain.errors import SurveySlugConflictError, VersionNotFoundError
from app.repositories import content_repo, surveys_repo
from app.schema.api.requests.surveys import CreateSurveyRequest, UpdateSurveyRequest
from app.schema.orm.core.survey import Survey, SurveyVersion

DEFAULT_RESPONSE_STORE_ID = 1  # TODO: This should be set to a real default response store ID


class SurveyService:
    """Service for survey and survey version operations."""

    # ── Surveys ───────────────────────────────────────────────────────────────

    def create_survey(self, db: Session, project_id: int, data: CreateSurveyRequest) -> Survey:
        try:
            survey = surveys_repo.create_survey(db, project_id, data)
            commit_or_rollback(db)
        except IntegrityError as exc:
            if isinstance(exc.orig, UniqueViolation) and "public_slug" in (exc.orig.diag.constraint_name or ""):
                raise SurveySlugConflictError() from None
            raise
        return survey

    def get_survey(self, db: Session, project_id: int, survey_id: int) -> Survey:
        return survey_rules.ensure_not_none(
            survey=surveys_repo.get_survey(db, project_id, survey_id),
            survey_id=survey_id,
            project_id=project_id,
        )

    def update_survey(self, db: Session, project_id: int, survey_id: int, data: UpdateSurveyRequest) -> Survey:
        survey = self.get_survey(db, project_id, survey_id)
        try:
            updated = surveys_repo.update_survey(db, survey, data)
            commit_or_rollback(db)
        except IntegrityError as exc:
            if isinstance(exc.orig, UniqueViolation) and "public_slug" in (exc.orig.diag.constraint_name or ""):
                raise SurveySlugConflictError() from None
            raise
        return updated

    def delete_survey(self, db: Session, project_id: int, survey_id: int) -> None:
        survey = self.get_survey(db, project_id, survey_id)
        survey_rules.ensure_can_delete_survey(survey)
        surveys_repo.delete_survey(db, survey)
        commit_or_rollback(db)

    # ── Survey versions ───────────────────────────────────────────────────────

    def _get_version(self, db: Session, survey_id: int, version_id: int) -> SurveyVersion:
        version = surveys_repo.get_version(db, survey_id, version_id)
        if version is None:
            raise VersionNotFoundError(survey_id=survey_id, version_id=version_id)
        return version

    def list_versions(self, db: Session, project_id: int, survey_id: int) -> list[SurveyVersion]:
        self.get_survey(db, project_id, survey_id)
        return surveys_repo.list_versions(db, survey_id)

    def get_version(self, db: Session, project_id: int, survey_id: int, version_id: int) -> SurveyVersion:
        self.get_survey(db, project_id, survey_id)
        return self._get_version(db, survey_id, version_id)

    def create_version(self, db: Session, project_id: int, survey_id: int) -> SurveyVersion:
        self.get_survey(db, project_id, survey_id)
        version = surveys_repo.create_version(db, survey_id)
        commit_or_rollback(db)
        return version

    def publish_version(self, db: Session, project_id: int, survey_id: int, version_id: int) -> SurveyVersion:
        survey = self.get_survey(db, project_id, survey_id)
        version = self._get_version(db, survey_id, version_id)

        version_rules.ensure_is_draft(version=version)

        questions = content_repo.list_questions(db, version.id)
        version_rules.ensure_has_questions(questions=questions)

        rules = content_repo.list_rules(db, version.id)
        scoring_rules = content_repo.list_scoring_rules(db, version.id)

        compiled = {
            "questions": [
                {"id": q.id, "question_key": q.question_key, "question_schema": q.question_schema} for q in questions
            ],
            "rules": [{"id": r.id, "rule_key": r.rule_key, "rule_schema": r.rule_schema} for r in rules],
            "scoring_rules": [
                {"id": s.id, "scoring_key": s.scoring_key, "scoring_schema": s.scoring_schema} for s in scoring_rules
            ],
        }
        survey_rules.ensure_default_response_store(
            survey=survey,
            default_response_store_id=DEFAULT_RESPONSE_STORE_ID,
        )

        result = surveys_repo.publish_version(db, survey, version, compiled)
        commit_or_rollback(db)
        return result

    def archive_version(self, db: Session, project_id: int, survey_id: int, version_id: int) -> SurveyVersion:
        self.get_survey(db, project_id, survey_id)
        version = self._get_version(db, survey_id, version_id)
        version_rules.ensure_can_archive(version=version)
        result = surveys_repo.archive_version(db, version)
        commit_or_rollback(db)
        return result
