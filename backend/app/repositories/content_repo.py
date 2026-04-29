from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
from app.schema.api.requests.content import (
    CreateNodeRequest,
    CreateScoringRuleRequest,
    UpdateNodeRequest,
    UpdateScoringRuleRequest,
)
from app.schema.orm.core.survey import SurveyVersion
from app.schema.orm.core.survey_content import SurveyQuestion, SurveyScoringRule

# ── Nodes (questions + rules) ──────────────────────────────────────────────────


def list_nodes(db: Session, version_id: int) -> list[SurveyQuestion]:
    return list(
        db.scalars(
            select(SurveyQuestion)
            .where(SurveyQuestion.survey_version_id == version_id)
            .order_by(SurveyQuestion.sort_key)
        )
    )


def list_questions(db: Session, version_id: int) -> list[SurveyQuestion]:
    """Return only question-type nodes. Used by version_rules.ensure_has_questions."""
    return list(
        db.scalars(
            select(SurveyQuestion)
            .where(SurveyQuestion.survey_version_id == version_id, SurveyQuestion.node_type == "question")
            .order_by(SurveyQuestion.sort_key)
        )
    )


def list_rules(db: Session, version_id: int) -> list[SurveyQuestion]:
    """Return only rule-type nodes. Used by version cloning."""
    return list(
        db.scalars(
            select(SurveyQuestion)
            .where(SurveyQuestion.survey_version_id == version_id, SurveyQuestion.node_type == "rule")
            .order_by(SurveyQuestion.sort_key)
        )
    )


def get_node(db: Session, version_id: int, node_id: int) -> SurveyQuestion | None:
    return db.scalar(
        select(SurveyQuestion).where(
            SurveyQuestion.survey_version_id == version_id,
            SurveyQuestion.id == node_id,
        )
    )


def create_node(db: Session, version: SurveyVersion, data: CreateNodeRequest) -> SurveyQuestion:
    node = SurveyQuestion(
        survey_version_id=version.id,
        question_key=data.content.id,
        sort_key=data.sort_key,
        node_type=data.type,
        question_schema=data.content.model_dump(by_alias=True, mode="json"),
    )
    db.add(node)
    flush_with_err_handle(db, contexts=[node])
    return node


def update_node(db: Session, node: SurveyQuestion, data: UpdateNodeRequest) -> SurveyQuestion:
    changed = data.model_fields_set
    if "sort_key" in changed and data.sort_key is not None:
        node.sort_key = data.sort_key
    if "content" in changed and data.content is not None:
        node.question_key = data.content.id
        node.question_schema = data.content.model_dump(by_alias=True, mode="json")
    flush_with_err_handle(db, contexts=[node])
    return node


def delete_node(db: Session, node: SurveyQuestion) -> None:
    db.delete(node)
    flush_with_err_handle(db, contexts=[node])


def clone_questions(db: Session, source_version: SurveyVersion, target_version: SurveyVersion) -> list[SurveyQuestion]:
    """Clone question-type nodes from one version to another. Used by surveys.py."""
    questions = list_questions(db, source_version.id)
    clones: list[SurveyQuestion] = []
    for source in questions:
        clone = SurveyQuestion(
            survey_version_id=target_version.id,
            question_key=source.question_key,
            sort_key=source.sort_key,
            node_type="question",
            question_schema=source.question_schema,
        )
        db.add(clone)
        clones.append(clone)
    if clones:
        flush_with_err_handle(db, contexts=clones)
    return clones


def clone_rules(db: Session, source_version: SurveyVersion, target_version: SurveyVersion) -> list[SurveyQuestion]:
    """Clone rule-type nodes from one version to another. Used by surveys.py."""
    rules = list_rules(db, source_version.id)
    clones: list[SurveyQuestion] = []
    for source in rules:
        clone = SurveyQuestion(
            survey_version_id=target_version.id,
            question_key=source.question_key,
            sort_key=source.sort_key,
            node_type="rule",
            question_schema=source.question_schema,
        )
        db.add(clone)
        clones.append(clone)
    if clones:
        flush_with_err_handle(db, contexts=clones)
    return clones


# ── Scoring rules ──────────────────────────────────────────────────────────────


def list_scoring_rules(db: Session, version_id: int) -> list[SurveyScoringRule]:
    return list(db.scalars(select(SurveyScoringRule).where(SurveyScoringRule.survey_version_id == version_id)))


def get_scoring_rule(db: Session, version_id: int, scoring_rule_id: int) -> SurveyScoringRule | None:
    return db.scalar(
        select(SurveyScoringRule).where(
            SurveyScoringRule.survey_version_id == version_id,
            SurveyScoringRule.id == scoring_rule_id,
        )
    )


def create_scoring_rule(db: Session, version: SurveyVersion, data: CreateScoringRuleRequest) -> SurveyScoringRule:
    rule = SurveyScoringRule(
        survey_version_id=version.id,
        scoring_key=data.scoring_key,
        scoring_schema=data.scoring_schema.model_dump(by_alias=True, mode="json"),
    )
    db.add(rule)
    flush_with_err_handle(db, contexts=[rule])
    return rule


def clone_scoring_rules(
    db: Session,
    source_version: SurveyVersion,
    target_version: SurveyVersion,
) -> list[SurveyScoringRule]:
    rules = list_scoring_rules(db, source_version.id)
    clones: list[SurveyScoringRule] = []
    for source in rules:
        clone = SurveyScoringRule(
            survey_version_id=target_version.id,
            scoring_key=source.scoring_key,
            scoring_schema=source.scoring_schema,
        )
        db.add(clone)
        clones.append(clone)
    if clones:
        flush_with_err_handle(db, contexts=clones)
    return clones


def update_scoring_rule(db: Session, rule: SurveyScoringRule, data: UpdateScoringRuleRequest) -> SurveyScoringRule:
    changed = data.model_fields_set
    if "scoring_key" in changed and data.scoring_key is not None:
        rule.scoring_key = data.scoring_key
    if "scoring_schema" in changed and data.scoring_schema is not None:
        rule.scoring_schema = data.scoring_schema.model_dump(by_alias=True, mode="json")
    flush_with_err_handle(db, contexts=[rule])
    return rule


def delete_scoring_rule(db: Session, rule: SurveyScoringRule) -> None:
    db.delete(rule)
    flush_with_err_handle(db, contexts=[rule])
