"""Survey answer validation engine.

Evaluates rule nodes against decrypted answers to determine effective
question state (visible / required), then validates that all visible +
required questions have non-cleared answers and that answer values match
their question family's canonical shape.

This module is pure domain logic — no DB access, no HTTP knowledge.
Callers load the survey nodes and decrypted answers, then call
``validate_submission``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.domain.errors import CompletionValidationError
from app.schema.api.submission_sessions import parse_answer_value
from app.schema.enums import AnswerFamily

logger = logging.getLogger(__name__)

KNOWN_FAMILIES: frozenset[str] = frozenset(AnswerFamily.__args__)  # type: ignore[attr-defined]


@dataclass(frozen=True, slots=True)
class QuestionNode:
    """Lightweight view of a question node for validation."""

    node_id: str
    family: str | None
    sort_key: int


@dataclass(frozen=True, slots=True)
class RuleNode:
    """Lightweight view of a rule node for validation."""

    sort_key: int
    rule_schema: dict[str, Any]


@dataclass(frozen=True, slots=True)
class DecryptedAnswer:
    """One decrypted answer mapped to its question node ID."""

    question_node_id: str
    answer_state: str
    answer_value: Any | None


@dataclass
class _QuestionState:
    visible: bool = True
    required: bool = False


@dataclass
class ValidationResult:  # noqa: D101
    missing_required: list[str] = field(default_factory=list)
    shape_errors: list[str] = field(default_factory=list)


def validate_submission(
    questions: list[QuestionNode],
    rule_nodes: list[RuleNode],
    answers: list[DecryptedAnswer],
) -> None:
    answer_map = _build_answer_map(answers)
    states = _evaluate_rules(questions, rule_nodes, answer_map)

    result = ValidationResult()
    _check_required(questions, states, answer_map, result)
    _check_answer_shapes(questions, answer_map, result)

    errors: list[str] = []
    if result.missing_required:
        errors.append(
            f"Missing required answers for {len(result.missing_required)} question(s)."
        )
    if result.shape_errors:
        errors.append(
            f"Invalid answer shape for {len(result.shape_errors)} question(s)."
        )
    if errors:
        raise CompletionValidationError(" ".join(errors))


def validate_answer_shape(family: str | None, answer_value: Any) -> None:
    """Validate a single answer value against its question family.

    Raises ``CompletionValidationError`` on shape mismatch, or silently
    returns if the family is unknown (graceful fallback).
    """
    if family is None or family not in KNOWN_FAMILIES:
        return
    try:
        parse_answer_value(family, answer_value)  # type: ignore[arg-type]
    except Exception as exc:
        raise CompletionValidationError(
            f"Answer value does not match the '{family}' schema: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_answer_map(answers: list[DecryptedAnswer]) -> dict[str, DecryptedAnswer]:
    result: dict[str, DecryptedAnswer] = {}
    for a in answers:
        existing = result.get(a.question_node_id)
        if existing is None or a.answer_state != "cleared":
            result[a.question_node_id] = a
    return result


def _evaluate_rules(
    questions: list[QuestionNode],
    rule_nodes: list[RuleNode],
    answer_map: dict[str, DecryptedAnswer],
) -> dict[str, _QuestionState]:
    states: dict[str, _QuestionState] = {
        q.node_id: _QuestionState() for q in questions
    }

    for rule in sorted(rule_nodes, key=lambda r: r.sort_key):
        schema = rule.rule_schema
        if_block = schema.get("if")
        if not if_block:
            continue

        condition_met = _evaluate_if(if_block, answer_map)
        branch = schema.get("then") if condition_met else schema.get("else")
        if branch is None:
            continue

        set_items = branch.get("set")
        if not set_items:
            continue

        for item in set_items:
            target_id = item.get("target_id")
            if target_id is None or target_id not in states:
                continue
            state = states[target_id]
            if item.get("visible") is not None:
                states[target_id] = _QuestionState(
                    visible=item["visible"], required=state.required
                )
            if item.get("required") is not None:
                states[target_id] = _QuestionState(
                    visible=states[target_id].visible, required=item["required"]
                )

    return states


def _evaluate_if(
    if_block: dict[str, Any],
    answer_map: dict[str, DecryptedAnswer],
) -> bool:
    match_mode = if_block.get("match", "ALL")
    conditions = if_block.get("conditions", [])
    if not conditions:
        return False

    results = [_evaluate_condition(c, answer_map) for c in conditions]

    if match_mode == "ALL":
        return all(results)
    elif match_mode == "ANY":
        return any(results)
    elif match_mode == "NONE":
        return not any(results)
    return False


def _evaluate_condition(
    condition: dict[str, Any],
    answer_map: dict[str, DecryptedAnswer],
) -> bool:
    target_id = condition.get("target_id")
    if target_id is None:
        return False

    answer = answer_map.get(target_id)
    if answer is None or answer.answer_state == "cleared":
        return False

    family = condition.get("family")
    requirements = condition.get("requirements")
    if not requirements:
        return False

    if family == "choice":
        return _check_choice(answer.answer_value, requirements)
    elif family == "matching":
        return _check_matching(answer.answer_value, requirements)
    elif family == "rating":
        return _check_rating(answer.answer_value, requirements)
    elif family == "field":
        return _check_field(answer.answer_value, requirements)

    return False


def _check_choice(value: Any, req: dict[str, Any]) -> bool:
    if not isinstance(value, dict):
        return False
    selected = set(value.get("selected", []))
    if not selected:
        return False

    required_ids = set(req.get("required", []))
    if required_ids and not required_ids.issubset(selected):
        return False

    forbidden_ids = set(req.get("forbidden", []))
    if forbidden_ids and forbidden_ids & selected:
        return False

    any_of_ids = set(req.get("any_of", []))
    return not (any_of_ids and not any_of_ids & selected)


def _check_matching(value: Any, req: dict[str, Any]) -> bool:
    if not isinstance(value, dict):
        return False
    pairs = value.get("pairs", [])
    if not isinstance(pairs, list):
        return False

    submitted = {(p.get("prompt_id"), p.get("match_id")) for p in pairs if isinstance(p, dict)}

    for rp in req.get("required", []):
        if not isinstance(rp, dict):
            continue
        if (rp.get("prompt_id"), rp.get("match_id")) not in submitted:
            return False
    return True


def _check_rating(value: Any, req: dict[str, Any]) -> bool:
    if not isinstance(value, dict):
        return False
    raw_val = value.get("number")
    if raw_val is None:
        return False
    try:
        num = float(raw_val)
    except (TypeError, ValueError):
        return False

    if req.get("min") is not None and num < req["min"]:
        return False
    return not (req.get("max") is not None and num > req["max"])


def _check_field(value: Any, req: dict[str, Any]) -> bool:
    if not isinstance(value, dict):
        return False
    field_type = req.get("type")
    if field_type == "number":
        return _check_number_field(value, req)
    elif field_type == "date":
        return _check_date_field(value, req)
    return False


def _check_number_field(value: dict[str, Any], req: dict[str, Any]) -> bool:
    raw = value.get("text")
    if raw is None:
        return False
    try:
        num = float(raw)
    except (TypeError, ValueError):
        return False

    op = req.get("operator")
    ref = req.get("value")
    if ref is None:
        return False

    _OPS = {
        "LT": float.__lt__, "LTE": float.__le__,
        "GT": float.__gt__, "GTE": float.__ge__,
        "EQ": float.__eq__, "NEQ": float.__ne__,
    }
    fn = _OPS.get(op)  # type: ignore[arg-type]
    return fn(num, float(ref)) if fn else False


def _check_date_field(value: dict[str, Any], req: dict[str, Any]) -> bool:
    raw = value.get("text")
    if raw is None:
        return False
    try:
        val_date = date.fromisoformat(raw)
    except (TypeError, ValueError):
        return False

    ref = req.get("value")
    if ref is None:
        return False
    try:
        ref_date = date.fromisoformat(ref)
    except (TypeError, ValueError):
        return False

    op = req.get("operator")
    if op == "before":
        return val_date < ref_date
    elif op == "after":
        return val_date > ref_date
    return False


def _check_required(
    questions: list[QuestionNode],
    states: dict[str, _QuestionState],
    answer_map: dict[str, DecryptedAnswer],
    result: ValidationResult,
) -> None:
    for q in questions:
        state = states.get(q.node_id)
        if state is None or not state.visible or not state.required:
            continue
        answer = answer_map.get(q.node_id)
        if answer is None or answer.answer_state == "cleared":
            result.missing_required.append(q.node_id)


def _check_answer_shapes(
    questions: list[QuestionNode],
    answer_map: dict[str, DecryptedAnswer],
    result: ValidationResult,
) -> None:
    family_by_id = {q.node_id: q.family for q in questions}
    for qid, answer in answer_map.items():
        if answer.answer_state == "cleared":
            continue
        family = family_by_id.get(qid)
        if family is None or family not in KNOWN_FAMILIES:
            continue
        try:
            parse_answer_value(family, answer.answer_value)  # type: ignore[arg-type]
        except Exception:
            result.shape_errors.append(qid)
