"""Document-wide publication checks that deliberately sit outside Pydantic."""

from __future__ import annotations

from typing import Any

import pytest

from app.domain.errors import SurveyPublishError
from app.domain.surveys.publication.issues import (
    CONDITION_DEPENDENCY_CYCLE,
    CONDITION_FIELD_MISSING,
    CONDITION_OPERATOR_INCOMPATIBLE,
    CONDITION_OPTION_MISSING,
    DUPLICATE_FIELD_ID,
    DUPLICATE_FIELD_KEY,
)
from app.domain.surveys.publication.validator import ensure_publishable, validate_for_publication
from app.schema.api.content.survey_document import SurveyDefinition


def _field(
    suffix: str,
    *,
    key: str | None = None,
    interaction: dict[str, Any] | None = None,
    response: dict[str, Any] | None = None,
    source: str | None = None,
    operator: str = "equals",
    value: object = "yes",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": f"field_{suffix}",
        "key": key or suffix,
        "prompt": f"Question {suffix}?",
        "interaction": interaction or {"kind": "text"},
        "response": response or {"type": "string"},
    }
    if source is not None:
        payload["behaviour"] = {
            "visibility": {
                "mode": "conditional",
                "condition": {
                    "fieldId": f"field_{source}",
                    "operator": operator,
                    "value": value,
                },
            }
        }
    return payload


def _definition(*fields: dict[str, Any]) -> SurveyDefinition:
    return SurveyDefinition.model_validate(
        {
            "document": {
                "sections": [
                    {
                        "id": "section_main",
                        "title": "Main",
                        "blocks": [
                            {"id": f"block_{index}", "type": "input", "field": field}
                            for index, field in enumerate(fields)
                        ],
                    }
                ]
            }
        }
    )


def _codes(definition: SurveyDefinition) -> list[str]:
    return [issue.code for issue in validate_for_publication(definition)]


def test_valid_definition_has_no_publication_issues() -> None:
    assert validate_for_publication(_definition(_field("name"))) == []


def test_valid_definition_is_publishable() -> None:
    ensure_publishable(_definition(_field("name")))


def test_invalid_definition_raises_error_with_publication_issues() -> None:
    definition = _definition(_field("dependent", source="missing"))

    with pytest.raises(SurveyPublishError) as exc_info:
        ensure_publishable(definition)

    error = exc_info.value
    assert error.status_code == 409
    assert error.code == "SURVEY_PUBLISH_ERROR"
    assert error.details == {
        "issues": [
            {
                "code": CONDITION_FIELD_MISSING,
                "message": "Referenced field 'field_missing' does not exist.",
                "object_id": "field_dependent",
            }
        ]
    }


def test_global_field_id_and_key_duplicates_are_reported() -> None:
    definition = _definition(
        _field("first", key="same"),
        _field("first", key="same"),
    )

    assert _codes(definition) == [DUPLICATE_FIELD_ID, DUPLICATE_FIELD_KEY]


def test_missing_condition_field_is_reported() -> None:
    definition = _definition(_field("dependent", source="missing"))

    assert _codes(definition) == [CONDITION_FIELD_MISSING]


def test_operator_must_match_referenced_response() -> None:
    definition = _definition(
        _field("source"),
        _field("dependent", source="source", operator="greater_than", value=2),
    )

    assert _codes(definition) == [CONDITION_OPERATOR_INCOMPATIBLE]


def test_choice_condition_option_must_exist() -> None:
    definition = _definition(
        _field(
            "source",
            interaction={
                "kind": "single_choice",
                "options": [{"id": "option_yes", "label": "Yes"}],
            },
            response={"type": "choice"},
        ),
        _field("dependent", source="source", value="option_no"),
    )

    assert _codes(definition) == [CONDITION_OPTION_MISSING]


def test_dependency_cycle_reports_each_participating_field() -> None:
    definition = _definition(
        _field("first", source="second"),
        _field("second", source="first"),
    )

    issues = validate_for_publication(definition)

    assert [issue.code for issue in issues] == [
        CONDITION_DEPENDENCY_CYCLE,
        CONDITION_DEPENDENCY_CYCLE,
    ]
    assert [issue.object_id for issue in issues] == ["field_first", "field_second"]


def test_duplicate_field_ids_do_not_create_misleading_cycle_issues() -> None:
    definition = _definition(
        _field("duplicate", key="first", source="other"),
        _field("duplicate", key="second", source="other"),
        _field("other", source="duplicate"),
    )

    assert _codes(definition) == [DUPLICATE_FIELD_ID]
