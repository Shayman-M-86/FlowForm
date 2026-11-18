from uuid import UUID

from app.schema.api.requests.content import (
    CreateScoringRuleRequest,
    UpdateScoringRuleRequest,
)
from app.schema.api.requests.content.ai_import import AIImportResponse
from app.schema.api.requests.content.node import (
    CreateQuestionNodeRequest,
    CreateRuleNodeRequest,
    UpdateNodeRequest,
)
from app.schema.orm.core.survey_content import SurveyQuestion, SurveyScoringRule
from sqlalchemy.orm import Session

from app.core.config import OpenAISettings
from app.db.error_handling import commit_with_err_handle
from app.domain import version_rules
from app.domain.errors import (
    NodeNotFoundError,
    ScoringRuleNotFoundError,
)
from app.domain.guards import ensure_present
from app.repositories import content_repo as cr
from app.schema.orm.core.survey import SurveyVersion
from app.schema.orm.core.user import User
from app.schema.types import ProjectId, SurveyId
from app.services.openai import OpenAIService
from app.services.surveys import SurveyService

_survey_service = SurveyService()
_openai_service = OpenAIService()


class ContentService:
    """Service for draft content operations on survey versions."""

    def _get_version(
        self, db: Session, project_id: ProjectId, survey_id: SurveyId, version_number: int
    ) -> SurveyVersion:
        return _survey_service._get_version(db, project_id, survey_id, version_number)

    def generate_ai_import(
        self,
        db: Session,
        project_id: ProjectId,
        survey_id: SurveyId,
        version_number: int,
        prompt: str,
        settings: OpenAISettings,
        actor: User,
    ) -> AIImportResponse:
        """Generate a preview only for an editable survey version."""
        version = self._get_version(db, project_id, survey_id, version_number)
        version_rules.ensure_is_editable(version=version)
        return _openai_service.generate(prompt, settings, user_key=str(actor.id))

    # ── Nodes (questions + rules) ──────────────────────────────────────────────

    def list_nodes(
        self,
        db: Session,
        project_id: ProjectId,
        survey_id: SurveyId,
        version_number: int,
        actor: User,  # noqa: ARG002
    ) -> list[SurveyQuestion]:
        version = self._get_version(db, project_id, survey_id, version_number)
        return cr.list_nodes(db, version.id)

    def create_node(
        self,
        db: Session,
        project_id: ProjectId,
        survey_id: SurveyId,
        version_number: int,
        data: CreateQuestionNodeRequest | CreateRuleNodeRequest,
        actor: User,  # noqa: ARG002
    ) -> SurveyQuestion:
        version = self._get_version(db, project_id, survey_id, version_number)
        version_rules.ensure_is_editable(version=version)
        node = cr.create_node(db, version, data)
        commit_with_err_handle(db, contexts=[node, version])
        return node

    def get_node(
        self,
        db: Session,
        project_id: ProjectId,
        survey_id: SurveyId,
        version_number: int,
        node_id: UUID,
        actor: User,  # noqa: ARG002
    ) -> SurveyQuestion:
        version = self._get_version(db, project_id, survey_id, version_number)
        return ensure_present(
            cr.get_node(db, version.id, node_id),
            error=NodeNotFoundError(),
        )

    def update_node(
        self,
        db: Session,
        project_id: ProjectId,
        survey_id: SurveyId,
        version_number: int,
        node_id: UUID,
        data: UpdateNodeRequest,
        actor: User,  # noqa: ARG002
    ) -> SurveyQuestion:
        version = self._get_version(db, project_id, survey_id, version_number)
        version_rules.ensure_is_editable(version=version)
        node = ensure_present(
            cr.get_node(db, version.id, node_id),
            error=NodeNotFoundError(),
        )
        updated = cr.update_node(db, node, data)
        commit_with_err_handle(db, contexts=[updated, version])
        return updated

    def delete_node(
        self,
        db: Session,
        project_id: ProjectId,
        survey_id: SurveyId,
        version_number: int,
        node_id: UUID,
        actor: User,  # noqa: ARG002
    ) -> None:
        version = self._get_version(db, project_id, survey_id, version_number)
        version_rules.ensure_is_editable(version=version)
        node = ensure_present(
            cr.get_node(db, version.id, node_id),
            error=NodeNotFoundError(),
        )
        cr.delete_node(db, node)
        commit_with_err_handle(db, contexts=[node, version])

    # ── Scoring rules ──────────────────────────────────────────────────────────

    def list_scoring_rules(
        self,
        db: Session,
        project_id: ProjectId,
        survey_id: SurveyId,
        version_number: int,
        actor: User,  # noqa: ARG002
    ) -> list[SurveyScoringRule]:
        version = self._get_version(db, project_id, survey_id, version_number)
        return cr.list_scoring_rules(db, version.id)

    def create_scoring_rule(
        self,
        db: Session,
        project_id: ProjectId,
        survey_id: SurveyId,
        version_number: int,
        data: CreateScoringRuleRequest,
        actor: User,  # noqa: ARG002
    ) -> SurveyScoringRule:
        version = self._get_version(db, project_id, survey_id, version_number)
        version_rules.ensure_is_editable(version=version)
        rule = cr.create_scoring_rule(db, version, data)
        commit_with_err_handle(db, contexts=[rule, version])
        return rule

    def get_scoring_rule(
        self,
        db: Session,
        project_id: ProjectId,
        survey_id: SurveyId,
        version_number: int,
        scoring_rule_id: int,
        actor: User,  # noqa: ARG002
    ) -> SurveyScoringRule:
        version = self._get_version(db, project_id, survey_id, version_number)
        return ensure_present(
            cr.get_scoring_rule(db, version.id, scoring_rule_id),
            error=ScoringRuleNotFoundError(),
        )

    def update_scoring_rule(
        self,
        db: Session,
        project_id: ProjectId,
        survey_id: SurveyId,
        version_number: int,
        scoring_rule_id: int,
        data: UpdateScoringRuleRequest,
        actor: User,  # noqa: ARG002
    ) -> SurveyScoringRule:
        version = self._get_version(db, project_id, survey_id, version_number)
        version_rules.ensure_is_editable(version=version)
        rule = ensure_present(
            cr.get_scoring_rule(db, version.id, scoring_rule_id),
            error=ScoringRuleNotFoundError(),
        )
        updated = cr.update_scoring_rule(db, rule, data)
        commit_with_err_handle(db, contexts=[updated, version])
        return updated

    def delete_scoring_rule(
        self,
        db: Session,
        project_id: ProjectId,
        survey_id: SurveyId,
        version_number: int,
        scoring_rule_id: int,
        actor: User,  # noqa: ARG002
    ) -> None:
        version = self._get_version(db, project_id, survey_id, version_number)
        version_rules.ensure_is_editable(version=version)
        rule = ensure_present(
            cr.get_scoring_rule(db, version.id, scoring_rule_id),
            error=ScoringRuleNotFoundError(),
        )
        cr.delete_scoring_rule(db, rule)
        commit_with_err_handle(db, contexts=[rule, version])
