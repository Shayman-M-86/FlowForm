"""Builders for survey definition tests."""

from __future__ import annotations

from typing import Any


def ulid(seed: str) -> str:
    body = seed.upper().replace("_", "0").replace("I", "1").replace("L", "1")
    body = body.replace("O", "0").replace("U", "V")
    return (body + "0" * 26)[:26]


def section_id(seed: str) -> str:
    return f"section_{ulid(seed)}"


def block_id(seed: str) -> str:
    return f"block_{ulid(seed)}"


def field_id(seed: str) -> str:
    return f"field_{ulid(seed)}"


def option_id(seed: str) -> str:
    return f"option_{ulid(seed)}"


def text_field(seed: str, **overrides: Any) -> dict[str, Any]:
    field: dict[str, Any] = {
        "id": field_id(seed),
        "key": seed.lower(),
        "prompt": f"Question {seed}?",
        "interaction": {"kind": "text"},
        "response": {"type": "string"},
    }
    field.update(overrides)
    return field


def choice_field(seed: str, option_seeds: list[str], **overrides: Any) -> dict[str, Any]:
    field: dict[str, Any] = {
        "id": field_id(seed),
        "key": seed.lower(),
        "prompt": f"Question {seed}?",
        "interaction": {
            "kind": "single_choice",
            "options": [{"id": option_id(seed), "label": seed.title()} for seed in option_seeds],
        },
        "response": {"type": "choice"},
    }
    field.update(overrides)
    return field


def input_block(seed: str, field: dict[str, Any]) -> dict[str, Any]:
    return {"id": block_id(seed), "type": "input", "field": field}


def section(seed: str, blocks: list[dict[str, Any]], **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": section_id(seed),
        "title": f"Section {seed}",
        "blocks": blocks,
    }
    payload.update(overrides)
    return payload


def definition(sections: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if sections is None:
        sections = [section("a", [input_block("b1", text_field("q1"))])]
    return {"document": {"sections": sections}}
