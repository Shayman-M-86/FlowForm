"""Contract coverage for the V2 data definitions, independent of route migration."""

import json

import pytest
from pydantic import TypeAdapter, ValidationError

from app.schema.api.requests.submission_sessions import (
    CompleteSubmissionSessionRequest,
    SaveSubmissionSessionAnswerRequest,
)
from app.schema.models.survey_document.document import SurveyContent

FIELD_UUID = "10000000-0000-4000-8000-000000000001"
OPTION_UUID = "20000000-0000-4000-8000-000000000001"
MUTATION_UUID = "60000000-0000-4000-8000-000000000001"
ANSWERS = TypeAdapter(SaveSubmissionSessionAnswerRequest)


def submission(spec, value):
    return {
        "field_uuid": FIELD_UUID,
        "client_mutation_id": MUTATION_UUID,
        "state": "answered",
        "answer_spec": spec,
        "answer_value": value,
    }


@pytest.mark.parametrize(
    ("spec", "value"),
    [
        ({"type": "string", "required": True}, "hello"),
        ({"type": "integer", "required": True, "constraints": {"min": 0, "max": 120}}, 24),
        ({"type": "number", "required": False}, 7.5),
        ({"type": "boolean", "required": True}, False),
        ({"type": "date", "required": True}, "2026-11-18"),
        ({"type": "choice", "required": True}, OPTION_UUID),
        ({"type": "choice_set", "required": False}, [OPTION_UUID]),
        (
            {"type": "object", "required": True, "valueType": "matching"},
            {"pairs": [{"prompt_uuid": FIELD_UUID, "match_uuid": OPTION_UUID}]},
        ),
    ],
)
def test_v2_answer_round_trip(spec, value):
    raw = submission(spec, value)
    answer = ANSWERS.validate_json(json.dumps(raw))
    assert answer.model_dump(mode="json", exclude_unset=True) == raw


@pytest.mark.parametrize(
    ("spec", "value"),
    [
        ({"type": "integer", "required": True}, True),
        ({"type": "integer", "required": True}, 1.5),
        ({"type": "number", "required": True}, "24"),
        ({"type": "boolean", "required": True}, 1),
        ({"type": "string", "required": True}, None),
        ({"type": "string", "required": True, "constraints": {"maxLength": 2}}, "long"),
        ({"type": "integer", "required": True, "constraints": {"max": 10}}, 11),
        ({"type": "integer", "required": True, "constraints": {"min": 10, "max": 0}}, 5),
        ({"type": "date", "required": True}, "2026-02-30"),
        ({"type": "choice", "required": True}, "readable_option_id"),
        ({"type": "choice_set", "required": True}, {"selected": [OPTION_UUID]}),
        ({"type": "choice_set", "required": True, "constraints": {"minSelections": 1}}, []),
        ({"type": "object", "required": True}, {}),
        ({"type": "object", "required": True, "valueType": "matching"}, {"pairs": [{"prompt_id": "a"}]}),
    ],
)
def test_v2_invalid_answer_rejected(spec, value):
    with pytest.raises(ValidationError):
        ANSWERS.validate_json(json.dumps(submission(spec, value)))


def test_v2_clear_omits_value_and_allows_spec():
    raw: dict[str, object] = {"field_uuid": FIELD_UUID, "client_mutation_id": MUTATION_UUID, "state": "cleared"}
    assert ANSWERS.validate_json(json.dumps(raw)).model_dump(mode="json", exclude_unset=True) == raw
    raw["answer_spec"] = {"type": "integer", "required": True}
    ANSWERS.validate_json(json.dumps(raw))
    raw["answer_value"] = None
    with pytest.raises(ValidationError):
        ANSWERS.validate_json(json.dumps(raw))


@pytest.mark.parametrize("missing", ["answer_value", "answer_spec", "client_mutation_id", "field_uuid"])
def test_v2_answer_required_properties(missing):
    raw = submission({"type": "integer", "required": True}, 24)
    del raw[missing]
    with pytest.raises(ValidationError):
        ANSWERS.validate_json(json.dumps(raw))


def test_v2_completion_contains_no_answers():
    assert CompleteSubmissionSessionRequest.model_validate_json('{"action":"complete"}').action == "complete"
    with pytest.raises(ValidationError):
        CompleteSubmissionSessionRequest.model_validate_json('{"action":"complete","answers":[]}')


def test_v2_survey_identity_structure_and_conditions():
    raw = {
        "title": "Screening",
        "workflow": {
            "rules": [
                {
                    "id": "underage",
                    "enabled": True,
                    "when": {"not": {"fieldUuid": FIELD_UUID, "operator": "is_answered"}},
                    "outcome": "unanswered",
                }
            ]
        },
        "sections": [
            {
                "id": "eligibility",
                "title": "Eligibility",
                "blocks": [
                    {"id": "heading", "type": "heading", "content": {"text": "Welcome", "level": 1}},
                    {
                        "id": "age_input",
                        "type": "input",
                        "field": {
                            "id": "age",
                            "uuid": FIELD_UUID,
                            "prompt": "How old are you?",
                            "interaction": {"kind": "number", "suffix": "years"},
                            "answerSpec": {"type": "integer", "required": True},
                        },
                    },
                ],
            }
        ],
    }
    model = SurveyContent.model_validate_json(json.dumps(raw))
    assert model.model_dump(mode="json", exclude_unset=True) == raw
    raw["sections"][0]["blocks"][1]["field"]["key"] = "legacy"
    with pytest.raises(ValidationError):
        SurveyContent.model_validate_json(json.dumps(raw))
