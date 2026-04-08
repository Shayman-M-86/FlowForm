from sqlalchemy import select
from sqlalchemy.orm import Session

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
        question_schema=data.question_schema,
    )
    db.add(question)
    db.flush()
    return question


def update_question(db: Session, question: SurveyQuestion, data: UpdateQuestionRequest) -> SurveyQuestion:
    changed = data.model_fields_set
    if "question_key" in changed and data.question_key is not None:
        question.question_key = data.question_key
    if "question_schema" in changed and data.question_schema is not None:
        question.question_schema = data.question_schema
    db.flush()
    return question


def delete_question(db: Session, question: SurveyQuestion) -> None:
    db.delete(question)
    db.flush()


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
        rule_schema=data.rule_schema,
    )
    db.add(rule)
    db.flush()
    return rule


def update_rule(db: Session, rule: SurveyRule, data: UpdateRuleRequest) -> SurveyRule:
    changed = data.model_fields_set
    if "rule_key" in changed and data.rule_key is not None:
        rule.rule_key = data.rule_key
    if "rule_schema" in changed and data.rule_schema is not None:
        rule.rule_schema = data.rule_schema
    db.flush()
    return rule


def delete_rule(db: Session, rule: SurveyRule) -> None:
    db.delete(rule)
    db.flush()


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
        scoring_schema=data.scoring_schema,
    )
    db.add(rule)
    db.flush()
    return rule


def update_scoring_rule(db: Session, rule: SurveyScoringRule, data: UpdateScoringRuleRequest) -> SurveyScoringRule:
    changed = data.model_fields_set
    if "scoring_key" in changed and data.scoring_key is not None:
        rule.scoring_key = data.scoring_key
    if "scoring_schema" in changed and data.scoring_schema is not None:
        rule.scoring_schema = data.scoring_schema
    db.flush()
    return rule


def delete_scoring_rule(db: Session, rule: SurveyScoringRule) -> None:
    db.delete(rule)
    db.flush()
