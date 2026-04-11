from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
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

# ── Questions ──────────────────────────────────────────────────────────────────


def list_questions(db: Session, version_id: int) -> list[SurveyQuestion]:
    return list(db.scalars(select(SurveyQuestion).where(SurveyQuestion.survey_version_id == version_id)))


def get_question(db: Session, version_id: int, question_id: int) -> SurveyQuestion | None:
    return db.scalar(
        select(SurveyQuestion).where(
            SurveyQuestion.survey_version_id == version_id,
            SurveyQuestion.id == question_id,
        )
    )


def create_question(db: Session, version: SurveyVersion, data: CreateQuestionRequest) -> SurveyQuestion:
    question = SurveyQuestion(
        survey_version_id=version.id,
        question_key=data.question_key,
        question_schema=data.question_schema.model_dump(by_alias=True, mode="json"),
    )
    db.add(question)
    flush_with_err_handle(db, contexts=[question])
    return question


def clone_questions(db: Session, source_version: SurveyVersion, target_version: SurveyVersion) -> list[SurveyQuestion]:
    questions = list_questions(db, source_version.id)
    clones: list[SurveyQuestion] = []
    for source in questions:
        clone = SurveyQuestion(
            survey_version_id=target_version.id,
            question_key=source.question_key,
            question_schema=source.question_schema,
        )
        db.add(clone)
        clones.append(clone)
    if clones:
        flush_with_err_handle(db, contexts=clones)
    return clones


def update_question(db: Session, question: SurveyQuestion, data: UpdateQuestionRequest) -> SurveyQuestion:
    changed = data.model_fields_set
    if "question_key" in changed and data.question_key is not None:
        question.question_key = data.question_key
    if "question_schema" in changed and data.question_schema is not None:
        question.question_schema = data.question_schema.model_dump(
            by_alias=True,
            mode="json",
        )
    flush_with_err_handle(db, contexts=[question])
    return question


def delete_question(db: Session, question: SurveyQuestion) -> None:
    db.delete(question)
    flush_with_err_handle(db, contexts=[question])


# ── Rules ──────────────────────────────────────────────────────────────────────


def list_rules(db: Session, version_id: int) -> list[SurveyRule]:
    return list(db.scalars(select(SurveyRule).where(SurveyRule.survey_version_id == version_id)))


def get_rule(db: Session, version_id: int, rule_id: int) -> SurveyRule | None:
    return db.scalar(
        select(SurveyRule).where(
            SurveyRule.survey_version_id == version_id,
            SurveyRule.id == rule_id,
        )
    )


def create_rule(db: Session, version: SurveyVersion, data: CreateRuleRequest) -> SurveyRule:
    rule = SurveyRule(
        survey_version_id=version.id,
        rule_key=data.rule_key,
        rule_schema=data.rule_schema.model_dump(by_alias=True, mode="json"),
    )
    db.add(rule)
    flush_with_err_handle(db, contexts=[rule])
    return rule


def clone_rules(db: Session, source_version: SurveyVersion, target_version: SurveyVersion) -> list[SurveyRule]:
    rules = list_rules(db, source_version.id)
    clones: list[SurveyRule] = []
    for source in rules:
        clone = SurveyRule(
            survey_version_id=target_version.id,
            rule_key=source.rule_key,
            rule_schema=source.rule_schema,
        )
        db.add(clone)
        clones.append(clone)
    if clones:
        flush_with_err_handle(db, contexts=clones)
    return clones


def update_rule(db: Session, rule: SurveyRule, data: UpdateRuleRequest) -> SurveyRule:
    changed = data.model_fields_set
    if "rule_key" in changed and data.rule_key is not None:
        rule.rule_key = data.rule_key
    if "rule_schema" in changed and data.rule_schema is not None:
        rule.rule_schema = data.rule_schema.model_dump(by_alias=True, mode="json")
    flush_with_err_handle(db, contexts=[rule])
    return rule


def delete_rule(db: Session, rule: SurveyRule) -> None:
    db.delete(rule)
    flush_with_err_handle(db, contexts=[rule])


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
