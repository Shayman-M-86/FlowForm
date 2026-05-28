#!/usr/bin/env python3
"""
Print a concrete JSON example for any Pydantic request model.

Usage (run from repo root or backend/):
    uv run backend/scripts/schema-example.py CreateNodeRequest
    uv run backend/scripts/schema-example.py ChoiceQuestionSchemaIn
    uv run backend/scripts/schema-example.py RatingQuestionSchemaIn
    uv run backend/scripts/schema-example.py RuleSchemaIn
    uv run backend/scripts/schema-example.py --list
"""
from __future__ import annotations

import json
import sys
from typing import Any

# ── Model registry ────────────────────────────────────────────────────────────
# Add new models here as they're created.

def _registry() -> dict[str, Any]:
    from app.schema.api.requests.content.node import CreateNodeRequest, UpdateNodeRequest
    from app.schema.api.requests.content.questions_schemas import (
        ChoiceQuestionSchemaIn,
        FieldQuestionSchemaIn,
        MatchingQuestionSchemaIn,
        RatingQuestionSchemaIn,
    )
    from app.schema.api.requests.content.rule_schemas import RuleSchemaIn
    from app.schema.api.requests.content.rules import CreateRuleRequest, UpdateRuleRequest
    from app.schema.api.requests.content.scoring_rule_schemas import ScoringRuleSchemaIn
    from app.schema.api.requests.content.scoring_rules import CreateScoringRuleRequest

    return {
        "CreateNodeRequest": CreateNodeRequest,
        "UpdateNodeRequest": UpdateNodeRequest,
        "ChoiceQuestionSchemaIn": ChoiceQuestionSchemaIn,
        "FieldQuestionSchemaIn": FieldQuestionSchemaIn,
        "MatchingQuestionSchemaIn": MatchingQuestionSchemaIn,
        "RatingQuestionSchemaIn": RatingQuestionSchemaIn,
        "RuleSchemaIn": RuleSchemaIn,
        "CreateRuleRequest": CreateRuleRequest,
        "UpdateRuleRequest": UpdateRuleRequest,
        "ScoringRuleSchemaIn": ScoringRuleSchemaIn,
        "CreateScoringRuleRequest": CreateScoringRuleRequest,
    }


# ── Example generator ─────────────────────────────────────────────────────────

def _example_value(schema: dict, defs: dict, depth: int = 0, field_name: str = "") -> Any:
    """Recursively build a concrete example value from a JSON Schema node."""
    if depth > 10:
        return None

    # Resolve $ref
    if "$ref" in schema:
        ref_name = schema["$ref"].split("/")[-1]
        return _example_value(defs.get(ref_name, {}), defs, depth + 1, field_name)

    # anyOf / oneOf — pick first non-null branch
    for key in ("anyOf", "oneOf"):
        if key in schema:
            for branch in schema[key]:
                if branch.get("type") != "null":
                    return _example_value(branch, defs, depth + 1, field_name)
            return None

    # allOf — merge properties (simplified)
    if "allOf" in schema:
        merged: dict = {}
        for part in schema["allOf"]:
            merged.update(_example_value(part, defs, depth + 1, field_name) or {})
        return merged or None

    typ = schema.get("type")

    if typ == "object" or "properties" in schema:
        props = schema.get("properties", {})
        required_fields = set(schema.get("required", props.keys()))
        result = {}
        for name, prop_schema in props.items():
            if name in required_fields or schema.get("additionalProperties") is False:
                result[name] = _example_value(prop_schema, defs, depth + 1, name)

        # Special case: ElseDoIn must have exactly one action — drop all but first
        action_keys = [k for k in ("skip_to", "end_and_submit", "end_and_discard") if k in result]
        if len(action_keys) > 1:
            for k in action_keys[1:]:
                del result[k]

        return result

    if typ == "array":
        items = schema.get("items", {})
        element = _example_value(items, defs, depth + 1, field_name)
        # Ensure array element is not None (would fail string validators)
        if element is None:
            element = "q1"
        return [element]

    if typ == "string":
        if "enum" in schema:
            return schema["enum"][0]
        if "const" in schema:
            return schema["const"]
        # Use field name to pick a meaningful value
        named = {
            "id": "q1",
            "rule_key": "r1",
            "question_key": "q1",
            "target_id": "q1",
            "skip_to": "q2",
            "label": "Example label",
            "title": "Example title",
            "placeholder": "Enter a value",
            "left_label": "Low",
            "right_label": "High",
            "value": "2023-01-01",
        }
        return named.get(field_name, f"example_{field_name}" if field_name else "example")

    if typ == "integer":
        if "const" in schema:
            return schema["const"]
        excl_min = schema.get("exclusiveMinimum")
        minimum = schema.get("minimum")
        if excl_min is not None:
            return int(excl_min) + 1
        if minimum is not None:
            return int(minimum)
        # Named numeric hints
        if field_name in ("min_selected", "min"):
            return 1
        if field_name in ("max_selected", "max", "stars"):
            return 3
        if field_name == "step":
            return 1
        if field_name == "sort_key":
            return 100000
        return 1

    if typ == "number":
        excl_min = schema.get("exclusiveMinimum")
        minimum = schema.get("minimum")
        if excl_min is not None:
            return float(excl_min) + 1.0
        if minimum is not None:
            return float(minimum) if float(minimum) > 0 else 1.0
        # Named hints for rating range
        if field_name == "min":
            return 1.0
        if field_name == "max":
            return 5.0
        if field_name == "step":
            return 1.0
        return 1.0

    if typ == "boolean":
        return True

    if typ == "null":
        return None

    return None


def _build_example(model_class: Any) -> dict:
    """Generate a concrete example dict for a Pydantic model."""
    # For wrapper models whose `content` is a union, generate the example by
    # building a concrete sub-model example and injecting it.
    from app.schema.api.requests.content.node import CreateNodeRequest, UpdateNodeRequest
    from app.schema.api.requests.content.questions_schemas import ChoiceQuestionSchemaIn

    if model_class in (CreateNodeRequest, UpdateNodeRequest):
        content_example = _build_example(ChoiceQuestionSchemaIn)
        raw: dict = {"type": "question", "sort_key": 100000, "content": content_example}
        if model_class is UpdateNodeRequest:
            raw = {"sort_key": 100000, "content": content_example}
        instance = model_class.model_validate(raw)
        return instance.model_dump(by_alias=True, mode="json")

    full_schema = model_class.model_json_schema(by_alias=True)
    defs = full_schema.get("$defs", {})
    raw = _example_value(full_schema, defs)

    try:
        instance = model_class.model_validate(raw)
        return instance.model_dump(by_alias=True, mode="json")
    except Exception as e:
        return {"__warning__": f"Could not validate example: {e}", "__raw__": raw}


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    import os
    import sys

    # Ensure the backend package is importable
    backend_dir = os.path.join(os.path.dirname(__file__), "..")
    sys.path.insert(0, os.path.abspath(backend_dir))

    args = sys.argv[1:]

    if not args or "--help" in args or "-h" in args:
        print(__doc__)
        sys.exit(0)

    registry = _registry()

    if "--list" in args:
        print("Available models:")
        for name in sorted(registry):
            print(f"  {name}")
        sys.exit(0)

    model_name = args[0]
    if model_name not in registry:
        close = [n for n in registry if model_name.lower() in n.lower()]
        print(f"Unknown model: {model_name}", file=sys.stderr)
        if close:
            print(f"Did you mean: {', '.join(close)}", file=sys.stderr)
        else:
            print(f"Run with --list to see available models.", file=sys.stderr)
        sys.exit(1)

    model_class = registry[model_name]
    example = _build_example(model_class)
    print(json.dumps(example, indent=2))


if __name__ == "__main__":
    main()
