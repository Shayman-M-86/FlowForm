from __future__ import annotations

from typing import cast

import pytest
from psycopg.errors import CheckViolation, NotNullViolation, UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from app.schema.orm.core.survey import SurveyVersion
from app.schema.orm.core.survey_content import SurveyQuestion, SurveyRule, SurveyScoringRule
from tests.integration.core.factories import (
    make_survey_question,
    make_survey_rule,
    make_survey_scoring_rule,
    make_survey_version,
)

# ---------------------------------------------------------------------------
# SurveyQuestion
# ---------------------------------------------------------------------------


def test_survey_question_can_be_created(db_session: scoped_session[Session], survey_version: SurveyVersion) -> None:
    """All fields are persisted and server defaults populate created_at and updated_at."""
    question = make_survey_question(
        survey_version.id, question_key="q1", question_schema={"type": "field", "label": "Name"}
    )
    db_session.add(question)
    db_session.flush()

    saved = db_session.get(SurveyQuestion, question.id)
    assert saved is not None, "SurveyQuestion was not persisted"
    assert saved.survey_version_id == survey_version.id, (
        f"survey_version_id={saved.survey_version_id!r}, expected {survey_version.id!r}"
    )
    assert saved.question_key == "q1", f"question_key={saved.question_key!r}, expected 'q1'"
    assert saved.question_schema == {"type": "field", "label": "Name"}, f"question_schema={saved.question_schema!r}"
    assert saved.created_at is not None, "created_at was not set by the server default"
    assert saved.updated_at is not None, "updated_at was not set by the server default"


def test_survey_question_unique_key_within_version(
    db_session: scoped_session[Session], survey_version: SurveyVersion
) -> None:
    """Two questions in the same survey version cannot share a question_key."""
    q_a = make_survey_question(survey_version.id, question_key="dup")
    db_session.add(q_a)
    db_session.flush()

    q_b = make_survey_question(survey_version.id, question_key="dup")
    db_session.add(q_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "uq_survey_questions_version_key", (
        f"Expected constraint 'uq_survey_questions_version_key', got '{constraint}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_question_same_key_allowed_across_versions(
    db_session: scoped_session[Session], survey_version: SurveyVersion
) -> None:
    """The same question_key may appear in different survey versions."""
    assert survey_version.created_by_user_id is not None
    v2 = make_survey_version(survey_version.survey_id, survey_version.created_by_user_id, version_number=2)
    db_session.add(v2)
    db_session.flush()

    q_a = make_survey_question(survey_version.id, question_key="shared")
    q_b = make_survey_question(v2.id, question_key="shared")
    db_session.add_all([q_a, q_b])
    db_session.flush()

    assert q_a.id != q_b.id, f"Expected distinct IDs across versions, got id={q_a.id!r} for both"


def test_survey_question_requires_question_key(
    db_session: scoped_session[Session], survey_version: SurveyVersion
) -> None:
    """question_key is NOT NULL — omitting it raises an IntegrityError."""
    question = make_survey_question(survey_version.id)
    question.question_key = None  # type: ignore[assignment]
    db_session.add(question)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "question_key", (
        f"Expected NOT NULL violation on 'question_key', got '{column}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_question_rejects_non_object_schema(
    db_session: scoped_session[Session], survey_version: SurveyVersion
) -> None:
    """question_schema must be a JSON object — arrays and scalars are rejected."""
    question = make_survey_question(survey_version.id)
    question.question_schema = ["not", "an", "object"]  # type: ignore[assignment]
    db_session.add(question)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_survey_questions_question_schema_is_object", (
        f"Expected constraint 'ck_survey_questions_question_schema_is_object', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_question_rejects_invalid_type(
    db_session: scoped_session[Session], survey_version: SurveyVersion
) -> None:
    """question_schema->>'type' must be one of: choice, field, matching, rating."""
    question = make_survey_question(survey_version.id, question_schema={"type": "text", "label": "Bad"})
    db_session.add(question)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_survey_questions_question_type_valid", (
        f"Expected constraint 'ck_survey_questions_question_type_valid', got '{constraint}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_question_cascades_on_version_delete(
    db_session: scoped_session[Session], survey_version: SurveyVersion
) -> None:
    """Deleting the survey version removes all its questions."""
    question = make_survey_question(survey_version.id)
    db_session.add(question)
    db_session.flush()

    question_id = question.id
    db_session.delete(survey_version)
    db_session.flush()
    db_session.expire_all()

    assert db_session.get(SurveyQuestion, question_id) is None, (
        "SurveyQuestion should have been deleted when its survey version was deleted"
    )


# ---------------------------------------------------------------------------
# SurveyRule
# ---------------------------------------------------------------------------


def test_survey_rule_can_be_created(db_session: scoped_session[Session], survey_version: SurveyVersion) -> None:
    """All fields are persisted and server defaults populate created_at and updated_at."""
    rule = make_survey_rule(survey_version.id, rule_key="r1", rule_schema={"condition": "always"})
    db_session.add(rule)
    db_session.flush()

    saved = db_session.get(SurveyRule, rule.id)
    assert saved is not None, "SurveyRule was not persisted"
    assert saved.survey_version_id == survey_version.id, (
        f"survey_version_id={saved.survey_version_id!r}, expected {survey_version.id!r}"
    )
    assert saved.rule_key == "r1", f"rule_key={saved.rule_key!r}, expected 'r1'"
    assert saved.rule_schema == {"condition": "always"}, f"rule_schema={saved.rule_schema!r}"
    assert saved.created_at is not None, "created_at was not set by the server default"
    assert saved.updated_at is not None, "updated_at was not set by the server default"


def test_survey_rule_unique_key_within_version(
    db_session: scoped_session[Session], survey_version: SurveyVersion
) -> None:
    """Two rules in the same survey version cannot share a rule_key."""
    r_a = make_survey_rule(survey_version.id, rule_key="dup")
    db_session.add(r_a)
    db_session.flush()

    r_b = make_survey_rule(survey_version.id, rule_key="dup")
    db_session.add(r_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "uq_survey_rules_version_key", (
        f"Expected constraint 'uq_survey_rules_version_key', got '{constraint}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_rule_same_key_allowed_across_versions(
    db_session: scoped_session[Session], survey_version: SurveyVersion
) -> None:
    """The same rule_key may appear in different survey versions."""
    assert survey_version.created_by_user_id is not None
    v2 = make_survey_version(survey_version.survey_id, survey_version.created_by_user_id, version_number=2)
    db_session.add(v2)
    db_session.flush()

    r_a = make_survey_rule(survey_version.id, rule_key="shared")
    r_b = make_survey_rule(v2.id, rule_key="shared")
    db_session.add_all([r_a, r_b])
    db_session.flush()

    assert r_a.id != r_b.id, f"Expected distinct IDs across versions, got id={r_a.id!r} for both"


def test_survey_rule_requires_rule_key(db_session: scoped_session[Session], survey_version: SurveyVersion) -> None:
    """rule_key is NOT NULL — omitting it raises an IntegrityError."""
    rule = make_survey_rule(survey_version.id)
    rule.rule_key = None  # type: ignore[assignment]
    db_session.add(rule)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "rule_key", (
        f"Expected NOT NULL violation on 'rule_key', got '{column}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_rule_rejects_non_object_schema(
    db_session: scoped_session[Session], survey_version: SurveyVersion
) -> None:
    """rule_schema must be a JSON object — arrays and scalars are rejected."""
    rule = make_survey_rule(survey_version.id)
    rule.rule_schema = ["not", "an", "object"]  # type: ignore[assignment]
    db_session.add(rule)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_survey_rules_rule_schema_is_object", (
        f"Expected constraint 'ck_survey_rules_rule_schema_is_object', got '{constraint}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_rule_cascades_on_version_delete(
    db_session: scoped_session[Session], survey_version: SurveyVersion
) -> None:
    """Deleting the survey version removes all its rules."""
    rule = make_survey_rule(survey_version.id)
    db_session.add(rule)
    db_session.flush()

    rule_id = rule.id
    db_session.delete(survey_version)
    db_session.flush()
    db_session.expire_all()

    assert db_session.get(SurveyRule, rule_id) is None, (
        "SurveyRule should have been deleted when its survey version was deleted"
    )


# ---------------------------------------------------------------------------
# SurveyScoringRule
# ---------------------------------------------------------------------------


def test_survey_scoring_rule_can_be_created(db_session: scoped_session[Session], survey_version: SurveyVersion) -> None:
    """All fields are persisted and server defaults populate created_at and updated_at."""
    scoring_rule = make_survey_scoring_rule(survey_version.id, scoring_key="s1", scoring_schema={"formula": "sum"})
    db_session.add(scoring_rule)
    db_session.flush()

    saved = db_session.get(SurveyScoringRule, scoring_rule.id)
    assert saved is not None, "SurveyScoringRule was not persisted"
    assert saved.survey_version_id == survey_version.id, (
        f"survey_version_id={saved.survey_version_id!r}, expected {survey_version.id!r}"
    )
    assert saved.scoring_key == "s1", f"scoring_key={saved.scoring_key!r}, expected 's1'"
    assert saved.scoring_schema == {"formula": "sum"}, f"scoring_schema={saved.scoring_schema!r}"
    assert saved.created_at is not None, "created_at was not set by the server default"
    assert saved.updated_at is not None, "updated_at was not set by the server default"


def test_survey_scoring_rule_unique_key_within_version(
    db_session: scoped_session[Session], survey_version: SurveyVersion
) -> None:
    """Two scoring rules in the same survey version cannot share a scoring_key."""
    s_a = make_survey_scoring_rule(survey_version.id, scoring_key="dup")
    db_session.add(s_a)
    db_session.flush()

    s_b = make_survey_scoring_rule(survey_version.id, scoring_key="dup")
    db_session.add(s_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "uq_survey_scoring_rules_version_key", (
        f"Expected constraint 'uq_survey_scoring_rules_version_key', got '{constraint}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_scoring_rule_same_key_allowed_across_versions(
    db_session: scoped_session[Session], survey_version: SurveyVersion
) -> None:
    """The same scoring_key may appear in different survey versions."""
    assert survey_version.created_by_user_id is not None
    v2 = make_survey_version(survey_version.survey_id, survey_version.created_by_user_id, version_number=2)
    db_session.add(v2)
    db_session.flush()

    s_a = make_survey_scoring_rule(survey_version.id, scoring_key="shared")
    s_b = make_survey_scoring_rule(v2.id, scoring_key="shared")
    db_session.add_all([s_a, s_b])
    db_session.flush()

    assert s_a.id != s_b.id, f"Expected distinct IDs across versions, got id={s_a.id!r} for both"


def test_survey_scoring_rule_requires_scoring_key(
    db_session: scoped_session[Session], survey_version: SurveyVersion
) -> None:
    """scoring_key is NOT NULL — omitting it raises an IntegrityError."""
    scoring_rule = make_survey_scoring_rule(survey_version.id)
    scoring_rule.scoring_key = None  # type: ignore[assignment]
    db_session.add(scoring_rule)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "scoring_key", (
        f"Expected NOT NULL violation on 'scoring_key', got '{column}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_scoring_rule_rejects_non_object_schema(
    db_session: scoped_session[Session], survey_version: SurveyVersion
) -> None:
    """scoring_schema must be a JSON object — arrays and scalars are rejected."""
    scoring_rule = make_survey_scoring_rule(survey_version.id)
    scoring_rule.scoring_schema = ["not", "an", "object"]  # type: ignore[assignment]
    db_session.add(scoring_rule)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_survey_scoring_rules_scoring_schema_is_object", (
        f"Expected constraint 'ck_survey_scoring_rules_scoring_schema_is_object', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_scoring_rule_cascades_on_version_delete(
    db_session: scoped_session[Session], survey_version: SurveyVersion
) -> None:
    """Deleting the survey version removes all its scoring rules."""
    scoring_rule = make_survey_scoring_rule(survey_version.id)
    db_session.add(scoring_rule)
    db_session.flush()

    scoring_rule_id = scoring_rule.id
    db_session.delete(survey_version)
    db_session.flush()
    db_session.expire_all()

    assert db_session.get(SurveyScoringRule, scoring_rule_id) is None, (
        "SurveyScoringRule should have been deleted when its survey version was deleted"
    )
