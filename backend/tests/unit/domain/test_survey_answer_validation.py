"""Unit tests for the survey answer validation engine."""
from __future__ import annotations

import pytest

from app.domain.errors import CompletionValidationError
from app.domain.survey_answer_validation import (
    DecryptedAnswer,
    QuestionNode,
    RuleNode,
    validate_answer_shape,
    validate_submission,
)


def _q(node_id: str, family: str = "choice", sort_key: int = 0) -> QuestionNode:
    return QuestionNode(node_id=node_id, family=family, sort_key=sort_key)


def _a(qid: str, state: str = "answered", value: object = None) -> DecryptedAnswer:
    return DecryptedAnswer(question_node_id=qid, answer_state=state, answer_value=value)


def _rule(
    sort_key: int,
    *,
    conditions: list[dict],
    match: str = "ALL",
    then_set: list[dict] | None = None,
    else_set: list[dict] | None = None,
) -> RuleNode:
    schema: dict = {
        "if": {"match": match, "conditions": conditions},
        "then": {"set": then_set or []},
    }
    if else_set is not None:
        schema["else"] = {"set": else_set}
    return RuleNode(sort_key=sort_key, rule_schema=schema)


# ---------------------------------------------------------------------------
# No rules — all questions visible, none required
# ---------------------------------------------------------------------------


class TestNoRules:
    def test_passes_with_no_rules_no_required(self):
        validate_submission([_q("q1")], [], [_a("q1", value={"selected": ["opt1"]})])

    def test_passes_with_no_answers_when_nothing_required(self):
        validate_submission([_q("q1")], [], [])


# ---------------------------------------------------------------------------
# Rule evaluation — visibility and required toggling
# ---------------------------------------------------------------------------


class TestRuleEvaluation:
    def test_rule_sets_required_on_condition_met(self):
        rule = _rule(
            1,
            conditions=[{"target_id": "q1", "family": "choice", "requirements": {"required": ["opt1"]}}],
            then_set=[{"target_id": "q2", "required": True}],
        )
        q1 = _q("q1", sort_key=0)
        q2 = _q("q2", sort_key=2)
        a1 = _a("q1", value={"selected": ["opt1"]})
        a2 = _a("q2", value={"selected": ["optA"]})

        validate_submission([q1, q2], [rule], [a1, a2])

    def test_rule_required_fails_when_answer_missing(self):
        rule = _rule(
            1,
            conditions=[{"target_id": "q1", "family": "choice", "requirements": {"required": ["opt1"]}}],
            then_set=[{"target_id": "q2", "required": True}],
        )
        q1 = _q("q1", sort_key=0)
        q2 = _q("q2", sort_key=2)
        a1 = _a("q1", value={"selected": ["opt1"]})

        with pytest.raises(CompletionValidationError, match="Missing required"):
            validate_submission([q1, q2], [rule], [a1])

    def test_invisible_required_question_not_enforced(self):
        rule = _rule(
            1,
            conditions=[{"target_id": "q1", "family": "choice", "requirements": {"required": ["opt1"]}}],
            then_set=[{"target_id": "q2", "visible": False, "required": True}],
        )
        q1 = _q("q1", sort_key=0)
        q2 = _q("q2", sort_key=2)
        a1 = _a("q1", value={"selected": ["opt1"]})

        validate_submission([q1, q2], [rule], [a1])

    def test_else_branch_applies_when_condition_not_met(self):
        rule = _rule(
            1,
            conditions=[{"target_id": "q1", "family": "choice", "requirements": {"required": ["opt1"]}}],
            then_set=[{"target_id": "q2", "required": True}],
            else_set=[{"target_id": "q3", "required": True}],
        )
        q1 = _q("q1", sort_key=0)
        q2 = _q("q2", sort_key=2)
        q3 = _q("q3", sort_key=3)
        a1 = _a("q1", value={"selected": ["opt99"]})
        a2 = _a("q2", value={"selected": ["x"]})

        with pytest.raises(CompletionValidationError, match="Missing required"):
            validate_submission([q1, q2, q3], [rule], [a1, a2])

    def test_match_any(self):
        rule = _rule(
            1,
            match="ANY",
            conditions=[
                {"target_id": "q1", "family": "choice", "requirements": {"required": ["opt1"]}},
                {"target_id": "q2", "family": "choice", "requirements": {"required": ["opt2"]}},
            ],
            then_set=[{"target_id": "q3", "required": True}],
        )
        q1 = _q("q1", sort_key=0)
        q2 = _q("q2", sort_key=1)
        q3 = _q("q3", sort_key=3)
        a2 = _a("q2", value={"selected": ["opt2"]})

        with pytest.raises(CompletionValidationError, match="Missing required"):
            validate_submission([q1, q2, q3], [rule], [a2])

    def test_match_none(self):
        rule = _rule(
            1,
            match="NONE",
            conditions=[{"target_id": "q1", "family": "choice", "requirements": {"required": ["opt1"]}}],
            then_set=[{"target_id": "q2", "required": True}],
        )
        q1 = _q("q1", sort_key=0)
        q2 = _q("q2", sort_key=2)

        with pytest.raises(CompletionValidationError, match="Missing required"):
            validate_submission([q1, q2], [rule], [])


# ---------------------------------------------------------------------------
# Condition family checkers
# ---------------------------------------------------------------------------


class TestChoiceCondition:
    def test_forbidden_blocks(self):
        rule = _rule(
            1,
            conditions=[{"target_id": "q1", "family": "choice", "requirements": {"forbidden": ["bad"]}}],
            then_set=[{"target_id": "q2", "required": True}],
        )
        q1 = _q("q1", sort_key=0)
        q2 = _q("q2", sort_key=2)
        a1 = _a("q1", value={"selected": ["bad"]})

        validate_submission([q1, q2], [rule], [a1])

    def test_any_of(self):
        rule = _rule(
            1,
            conditions=[{"target_id": "q1", "family": "choice", "requirements": {"any_of": ["a", "b"]}}],
            then_set=[{"target_id": "q2", "required": True}],
        )
        q1 = _q("q1", sort_key=0)
        q2 = _q("q2", sort_key=2)
        a1 = _a("q1", value={"selected": ["b"]})

        with pytest.raises(CompletionValidationError, match="Missing required"):
            validate_submission([q1, q2], [rule], [a1])


class TestRatingCondition:
    def test_min_max(self):
        rule = _rule(
            1,
            conditions=[{"target_id": "q1", "family": "rating", "requirements": {"min": 3, "max": 5}}],
            then_set=[{"target_id": "q2", "required": True}],
        )
        q1 = _q("q1", family="rating", sort_key=0)
        q2 = _q("q2", sort_key=2)
        a1 = _a("q1", value={"number": 4, "variant": "stars"})

        with pytest.raises(CompletionValidationError, match="Missing required"):
            validate_submission([q1, q2], [rule], [a1])

    def test_below_min_fails_condition(self):
        rule = _rule(
            1,
            conditions=[{"target_id": "q1", "family": "rating", "requirements": {"min": 3}}],
            then_set=[{"target_id": "q2", "required": True}],
        )
        q1 = _q("q1", family="rating", sort_key=0)
        q2 = _q("q2", sort_key=2)
        a1 = _a("q1", value={"number": 1, "variant": "stars"})

        validate_submission([q1, q2], [rule], [a1])


class TestFieldCondition:
    def test_number_gt(self):
        rule = _rule(
            1,
            conditions=[{
                "target_id": "q1", "family": "field",
                "requirements": {"type": "number", "operator": "GT", "value": 10},
            }],
            then_set=[{"target_id": "q2", "required": True}],
        )
        q1 = _q("q1", family="field", sort_key=0)
        q2 = _q("q2", sort_key=2)
        a1 = _a("q1", value={"field_type": "number", "text": "15"})

        with pytest.raises(CompletionValidationError, match="Missing required"):
            validate_submission([q1, q2], [rule], [a1])

    def test_date_before(self):
        rule = _rule(
            1,
            conditions=[{
                "target_id": "q1", "family": "field",
                "requirements": {"type": "date", "operator": "before", "value": "2026-01-01"},
            }],
            then_set=[{"target_id": "q2", "required": True}],
        )
        q1 = _q("q1", family="field", sort_key=0)
        q2 = _q("q2", sort_key=2)
        a1 = _a("q1", value={"field_type": "date", "text": "2025-06-15"})

        with pytest.raises(CompletionValidationError, match="Missing required"):
            validate_submission([q1, q2], [rule], [a1])


class TestMatchingCondition:
    def test_required_pairs(self):
        rule = _rule(
            1,
            conditions=[{
                "target_id": "q1", "family": "matching",
                "requirements": {"required": [{"prompt_id": "p1", "match_id": "m1"}]},
            }],
            then_set=[{"target_id": "q2", "required": True}],
        )
        q1 = _q("q1", family="matching", sort_key=0)
        q2 = _q("q2", sort_key=2)
        a1 = _a("q1", value={"pairs": [{"prompt_id": "p1", "match_id": "m1"}]})

        with pytest.raises(CompletionValidationError, match="Missing required"):
            validate_submission([q1, q2], [rule], [a1])


# ---------------------------------------------------------------------------
# Answer shape validation
# ---------------------------------------------------------------------------


class TestAnswerShapeValidation:
    def test_valid_choice_shape(self):
        validate_answer_shape("choice", {"selected": ["opt1"]})

    def test_invalid_choice_shape(self):
        with pytest.raises(CompletionValidationError, match="choice"):
            validate_answer_shape("choice", {"wrong": "shape"})

    def test_unknown_family_passes(self):
        validate_answer_shape("unknown_family", {"anything": True})

    def test_none_family_passes(self):
        validate_answer_shape(None, {"anything": True})

    def test_submission_rejects_bad_shape(self):
        q1 = _q("q1", family="choice")
        a1 = _a("q1", value={"wrong": "shape"})
        with pytest.raises(CompletionValidationError, match="Invalid answer shape"):
            validate_submission([q1], [], [a1])


# ---------------------------------------------------------------------------
# Cleared answers
# ---------------------------------------------------------------------------


class TestClearedAnswers:
    def test_cleared_answer_excluded_from_required(self):
        rule = _rule(
            1,
            conditions=[{"target_id": "q1", "family": "choice", "requirements": {"required": ["opt1"]}}],
            then_set=[{"target_id": "q2", "required": True}],
            else_set=[{"target_id": "q2", "required": True}],
        )
        q1 = _q("q1", sort_key=0)
        q2 = _q("q2", sort_key=2)
        a2 = _a("q2", state="cleared")

        with pytest.raises(CompletionValidationError, match="Missing required"):
            validate_submission([q1, q2], [rule], [a2])

    def test_cleared_answer_shape_not_validated(self):
        q1 = _q("q1", family="choice")
        a1 = _a("q1", state="cleared", value={"bad": "shape"})
        validate_submission([q1], [], [a1])
