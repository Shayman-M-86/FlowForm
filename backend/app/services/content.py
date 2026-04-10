from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.transaction import commit_or_rollback
from app.domain import version_rules
from app.domain.errors import (
    ContentKeyConflictError,
    QuestionNotFoundError,
    RuleNotFoundError,
    ScoringRuleNotFoundError,
)
from app.repositories import content_repo
from app.schema.api.requests.content import (
    CreateQuestionRequest,
    CreateRuleRequest,
    CreateScoringRuleRequest,
    UpdateQuestionRequest,
    UpdateRuleRequest,
    UpdateScoringRuleRequest,
)
from app.schema.orm.core.survey import SurveyVersion
from app.schema.orm.core.survey_content import SurveyQuestion, SurveyRule, SurveyScoringRule
from app.schema.orm.core.user import User
from app.services.access import (
    PERMISSIONS,
    require_survey_permission,
)
from app.services.surveys import SurveyService

_survey_service = SurveyService()


class ContentService:
    """Service for draft content operations on survey versions."""

    def _get_version(self, db: Session, project_id: int, survey_id: int, version_number: int) -> SurveyVersion:
        return _survey_service._get_version(db, project_id, survey_id, version_number)

    # ── Questions ──────────────────────────────────────────────────────────────
    @require_survey_permission(PERMISSIONS.survey.view)
    def list_questions(
        self, db: Session, project_id: int, survey_id: int, version_number: int, actor: User # noqa: ARG002
    ) -> list[SurveyQuestion]:
        version = self._get_version(db, project_id, survey_id, version_number)
        return content_repo.list_questions(db, version.id)

    @require_survey_permission(PERMISSIONS.survey.edit)
    def create_question(
        self,
        db: Session,
        project_id: int,
        survey_id: int,
        version_number: int,
        data: CreateQuestionRequest,
        actor: User, # noqa: ARG002
    ) -> SurveyQuestion:
        version = self._get_version(db, project_id, survey_id, version_number)
        version_rules.ensure_is_editable(version=version)
        try:
            question = content_repo.create_question(db, version, data)
            commit_or_rollback(db)
        except IntegrityError:
            raise ContentKeyConflictError("Duplicate question_key in this version") from None
        return question

    @require_survey_permission(PERMISSIONS.survey.view)
    def get_question(
        self, db: Session, project_id: int, survey_id: int, version_number: int, question_id: int
    ) -> SurveyQuestion:
        version = self._get_version(db, project_id, survey_id, version_number)
        question = content_repo.get_question(db, version.id, question_id)
        if question is None:
            raise QuestionNotFoundError()
        return question

    @require_survey_permission(PERMISSIONS.survey.edit)
    def update_question(
        self,
        db: Session,
        project_id: int,
        survey_id: int,
        version_number: int,
        question_id: int,
        data: UpdateQuestionRequest,
    ) -> SurveyQuestion:
        version = self._get_version(db, project_id, survey_id, version_number)
        version_rules.ensure_is_editable(version=version)
        question = content_repo.get_question(db, version.id, question_id)
        if question is None:
            raise QuestionNotFoundError()
        try:
            updated = content_repo.update_question(db, question, data)
            commit_or_rollback(db)
        except IntegrityError:
            raise ContentKeyConflictError("Duplicate question_key in this version") from None
        return updated

    @require_survey_permission(PERMISSIONS.survey.edit)
    def delete_question(
        self, db: Session, project_id: int, survey_id: int, version_number: int, question_id: int
    ) -> None:
        version = self._get_version(db, project_id, survey_id, version_number)
        version_rules.ensure_is_editable(version=version)
        question = content_repo.get_question(db, version.id, question_id)
        if question is None:
            raise QuestionNotFoundError()
        content_repo.delete_question(db, question)
        commit_or_rollback(db)

    # ── Rules ──────────────────────────────────────────────────────────────────
    @require_survey_permission(PERMISSIONS.survey.view)
    def list_rules(self, db: Session, project_id: int, survey_id: int, version_number: int) -> list[SurveyRule]:
        version = self._get_version(db, project_id, survey_id, version_number)
        return content_repo.list_rules(db, version.id)

    @require_survey_permission(PERMISSIONS.survey.edit)
    def create_rule(
        self, db: Session, project_id: int, survey_id: int, version_number: int, data: CreateRuleRequest
    ) -> SurveyRule:
        version = self._get_version(db, project_id, survey_id, version_number)
        version_rules.ensure_is_editable(version=version)
        try:
            rule = content_repo.create_rule(db, version, data)
            commit_or_rollback(db)
        except IntegrityError:
            raise ContentKeyConflictError("Duplicate rule_key in this version") from None
        return rule

    @require_survey_permission(PERMISSIONS.survey.view)
    def get_rule(self, db: Session, project_id: int, survey_id: int, version_number: int, rule_id: int) -> SurveyRule:
        version = self._get_version(db, project_id, survey_id, version_number)
        rule = content_repo.get_rule(db, version.id, rule_id)
        if rule is None:
            raise RuleNotFoundError()
        return rule

    @require_survey_permission(PERMISSIONS.survey.edit)
    def update_rule(
        self,
        db: Session,
        project_id: int,
        survey_id: int,
        version_number: int,
        rule_id: int,
        data: UpdateRuleRequest,
    ) -> SurveyRule:
        version = self._get_version(db, project_id, survey_id, version_number)
        version_rules.ensure_is_editable(version=version)
        rule = content_repo.get_rule(db, version.id, rule_id)
        if rule is None:
            raise RuleNotFoundError()
        try:
            updated = content_repo.update_rule(db, rule, data)
            commit_or_rollback(db)
        except IntegrityError:
            raise ContentKeyConflictError("Duplicate rule_key in this version") from None
        return updated

    @require_survey_permission(PERMISSIONS.survey.edit)
    def delete_rule(self, db: Session, project_id: int, survey_id: int, version_number: int, rule_id: int) -> None:
        version = self._get_version(db, project_id, survey_id, version_number)
        version_rules.ensure_is_editable(version=version)
        rule = content_repo.get_rule(db, version.id, rule_id)
        if rule is None:
            raise RuleNotFoundError()
        content_repo.delete_rule(db, rule)
        commit_or_rollback(db)

    # ── Scoring rules ──────────────────────────────────────────────────────────
    @require_survey_permission(PERMISSIONS.survey.view)
    def list_scoring_rules(
        self, db: Session, project_id: int, survey_id: int, version_number: int
    ) -> list[SurveyScoringRule]:
        version = self._get_version(db, project_id, survey_id, version_number)
        return content_repo.list_scoring_rules(db, version.id)

    @require_survey_permission(PERMISSIONS.survey.edit)
    def create_scoring_rule(
        self, db: Session, project_id: int, survey_id: int, version_number: int, data: CreateScoringRuleRequest
    ) -> SurveyScoringRule:
        version = self._get_version(db, project_id, survey_id, version_number)
        version_rules.ensure_is_editable(version=version)
        try:
            rule = content_repo.create_scoring_rule(db, version, data)
            commit_or_rollback(db)
        except IntegrityError:
            raise ContentKeyConflictError("Duplicate scoring_key in this version") from None
        return rule

    @require_survey_permission(PERMISSIONS.survey.view)
    def get_scoring_rule(
        self, db: Session, project_id: int, survey_id: int, version_number: int, scoring_rule_id: int
    ) -> SurveyScoringRule:
        version = self._get_version(db, project_id, survey_id, version_number)
        rule = content_repo.get_scoring_rule(db, version.id, scoring_rule_id)
        if rule is None:
            raise ScoringRuleNotFoundError()
        return rule

    @require_survey_permission(PERMISSIONS.survey.edit)
    def update_scoring_rule(
        self,
        db: Session,
        project_id: int,
        survey_id: int,
        version_number: int,
        scoring_rule_id: int,
        data: UpdateScoringRuleRequest,
    ) -> SurveyScoringRule:
        version = self._get_version(db, project_id, survey_id, version_number)
        version_rules.ensure_is_editable(version=version)
        rule = content_repo.get_scoring_rule(db, version.id, scoring_rule_id)
        if rule is None:
            raise ScoringRuleNotFoundError()
        try:
            updated = content_repo.update_scoring_rule(db, rule, data)
            commit_or_rollback(db)
        except IntegrityError:
            raise ContentKeyConflictError("Duplicate scoring_key in this version") from None
        return updated

    @require_survey_permission(PERMISSIONS.survey.edit)
    def delete_scoring_rule(
        self, db: Session, project_id: int, survey_id: int, version_number: int, scoring_rule_id: int
    ) -> None:
        version = self._get_version(db, project_id, survey_id, version_number)
        version_rules.ensure_is_editable(version=version)
        rule = content_repo.get_scoring_rule(db, version.id, scoring_rule_id)
        if rule is None:
            raise ScoringRuleNotFoundError()
        content_repo.delete_scoring_rule(db, rule)
        commit_or_rollback(db)
