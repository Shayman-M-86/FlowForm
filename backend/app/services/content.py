from sqlalchemy.orm import Session

from app.db.error_handling import commit_with_err_handle
from app.domain import version_rules
from app.domain.errors import (
    NodeNotFoundError,
    ScoringRuleNotFoundError,
)
from app.domain.permissions import PERMISSIONS
from app.repositories import content_repo
from app.schema.api.requests.content import (
    CreateNodeRequest,
    CreateScoringRuleRequest,
    UpdateNodeRequest,
    UpdateScoringRuleRequest,
)
from app.schema.orm.core.survey import SurveyVersion
from app.schema.orm.core.survey_content import SurveyQuestion, SurveyScoringRule
from app.schema.orm.core.user import User
from app.services.access.access_service import require_survey_permission
from app.services.surveys import SurveyService

_survey_service = SurveyService()


class ContentService:
    """Service for draft content operations on survey versions."""

    def _get_version(self, db: Session, project_id: int, survey_id: int, version_number: int) -> SurveyVersion:
        return _survey_service._get_version(db, project_id, survey_id, version_number)

    # ── Nodes (questions + rules) ──────────────────────────────────────────────

    @require_survey_permission(PERMISSIONS.survey.view)
    def list_nodes(
        self,
        db: Session,
        project_id: int,
        survey_id: int,
        version_number: int,
        actor: User,  # noqa: ARG002
    ) -> list[SurveyQuestion]:
        version = self._get_version(db, project_id, survey_id, version_number)
        return content_repo.list_nodes(db, version.id)

    @require_survey_permission(PERMISSIONS.survey.edit)
    def create_node(
        self,
        db: Session,
        project_id: int,
        survey_id: int,
        version_number: int,
        data: CreateNodeRequest,
        actor: User,  # noqa: ARG002
    ) -> SurveyQuestion:
        version = self._get_version(db, project_id, survey_id, version_number)
        version_rules.ensure_is_editable(version=version)
        node = content_repo.create_node(db, version, data)
        commit_with_err_handle(db, contexts=[node, version])
        return node

    @require_survey_permission(PERMISSIONS.survey.view)
    def get_node(
        self,
        db: Session,
        project_id: int,
        survey_id: int,
        version_number: int,
        node_id: int,
        actor: User,  # noqa: ARG002
    ) -> SurveyQuestion:
        version = self._get_version(db, project_id, survey_id, version_number)
        node = content_repo.get_node(db, version.id, node_id)
        if node is None:
            raise NodeNotFoundError()
        return node

    @require_survey_permission(PERMISSIONS.survey.edit)
    def update_node(
        self,
        db: Session,
        project_id: int,
        survey_id: int,
        version_number: int,
        node_id: int,
        data: UpdateNodeRequest,
        actor: User,  # noqa: ARG002
    ) -> SurveyQuestion:
        version = self._get_version(db, project_id, survey_id, version_number)
        version_rules.ensure_is_editable(version=version)
        node = content_repo.get_node(db, version.id, node_id)
        if node is None:
            raise NodeNotFoundError()
        updated = content_repo.update_node(db, node, data)
        commit_with_err_handle(db, contexts=[updated, version])
        return updated

    @require_survey_permission(PERMISSIONS.survey.edit)
    def delete_node(
        self,
        db: Session,
        project_id: int,
        survey_id: int,
        version_number: int,
        node_id: int,
        actor: User,  # noqa: ARG002
    ) -> None:
        version = self._get_version(db, project_id, survey_id, version_number)
        version_rules.ensure_is_editable(version=version)
        node = content_repo.get_node(db, version.id, node_id)
        if node is None:
            raise NodeNotFoundError()
        content_repo.delete_node(db, node)
        commit_with_err_handle(db, contexts=[node, version])

    # ── Scoring rules ──────────────────────────────────────────────────────────

    @require_survey_permission(PERMISSIONS.survey.view)
    def list_scoring_rules(
        self,
        db: Session,
        project_id: int,
        survey_id: int,
        version_number: int,
        actor: User,  # noqa: ARG002
    ) -> list[SurveyScoringRule]:
        version = self._get_version(db, project_id, survey_id, version_number)
        return content_repo.list_scoring_rules(db, version.id)

    @require_survey_permission(PERMISSIONS.survey.edit)
    def create_scoring_rule(
        self,
        db: Session,
        project_id: int,
        survey_id: int,
        version_number: int,
        data: CreateScoringRuleRequest,
        actor: User,  # noqa: ARG002
    ) -> SurveyScoringRule:
        version = self._get_version(db, project_id, survey_id, version_number)
        version_rules.ensure_is_editable(version=version)
        rule = content_repo.create_scoring_rule(db, version, data)
        commit_with_err_handle(db, contexts=[rule, version])
        return rule

    @require_survey_permission(PERMISSIONS.survey.view)
    def get_scoring_rule(
        self,
        db: Session,
        project_id: int,
        survey_id: int,
        version_number: int,
        scoring_rule_id: int,
        actor: User,  # noqa: ARG002
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
        actor: User,  # noqa: ARG002
    ) -> SurveyScoringRule:
        version = self._get_version(db, project_id, survey_id, version_number)
        version_rules.ensure_is_editable(version=version)
        rule = content_repo.get_scoring_rule(db, version.id, scoring_rule_id)
        if rule is None:
            raise ScoringRuleNotFoundError()
        updated = content_repo.update_scoring_rule(db, rule, data)
        commit_with_err_handle(db, contexts=[updated, version])
        return updated

    @require_survey_permission(PERMISSIONS.survey.edit)
    def delete_scoring_rule(
        self,
        db: Session,
        project_id: int,
        survey_id: int,
        version_number: int,
        scoring_rule_id: int,
        actor: User,  # noqa: ARG002
    ) -> None:
        version = self._get_version(db, project_id, survey_id, version_number)
        version_rules.ensure_is_editable(version=version)
        rule = content_repo.get_scoring_rule(db, version.id, scoring_rule_id)
        if rule is None:
            raise ScoringRuleNotFoundError()
        content_repo.delete_scoring_rule(db, rule)
        commit_with_err_handle(db, contexts=[rule, version])
