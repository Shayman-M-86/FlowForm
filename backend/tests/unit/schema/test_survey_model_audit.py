"""Typed survey document, answer, and condition contracts."""

import ast
from datetime import date
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from app.schema.models.survey_document.answer_spec import AnswerSpec
from app.schema.models.survey_document.answers import AnsweredAnswer
from app.schema.models.survey_document.conditions import Condition
from app.schema.models.survey_document.document import HeadingContent, NoticeContent, SurveyDefinition, SurveySection
from app.schema.models.survey_document.fields import Interaction, TextInteraction

FIELD = "10000000-0000-4000-8000-000000000001"


def definition():
    return {
        "id": "survey",
        "versionId": 1,
        "revision": 1,
        "title": "Survey",
        "projectName": "Research",
        "status": "draft",
        "document": {"sections": []},
    }


def test_document_version_is_the_shared_numeric_identity():
    assert SurveyDefinition.model_validate(definition()).versionId == 1
    for bad in ["version_001", 0, -1, 2**63]:
        with pytest.raises(ValidationError):
            SurveyDefinition.model_validate(definition() | {"versionId": bad})
    document = SurveyDefinition.model_json_schema()
    reference = document["properties"]["versionId"]["$ref"].split("/")[-1]
    schema = document["$defs"][reference]
    assert schema["type"] == "integer" and schema["minimum"] == 1


@pytest.mark.parametrize("bad", [0, 7, True, "1"])
def test_heading_levels_are_bounded_integers(bad):
    HeadingContent(text="Heading", level=6)
    with pytest.raises(ValidationError):
        HeadingContent(text="Heading", level=bad)


def test_notice_and_section_text_rules():
    assert NoticeContent(tone="info", title=" Notice ", text="  content  ").text == "  content  "
    for bad in [{"tone": "arbitrary"}, {"title": " "}, {"title": "x" * 201}, {"text": "x" * 10001}]:
        with pytest.raises(ValidationError):
            NoticeContent.model_validate({"tone": "info", "title": "Notice", "text": "Text"} | bad)
    with pytest.raises(ValidationError):
        SurveySection(id="s", title=" ", blocks=[])


def test_interactions_expose_only_their_presentations():
    TextInteraction(kind="short_text", placeholder="x" * 200)
    with pytest.raises(ValidationError):
        TextInteraction(kind="short_text", placeholder="x" * 201)
    adapter = TypeAdapter(Interaction)
    for raw in [
        {"kind": "rating", "presentation": "radio"},
        {"kind": "boolean", "presentation": "calendar"},
        {"kind": "single_choice", "presentation": "checkboxes", "options": []},
        {"kind": "multiple_choice", "presentation": "radio", "options": []},
    ]:
        with pytest.raises(ValidationError):
            adapter.validate_python(raw)


def test_conditions_are_operator_specific_and_recursive():
    adapter = TypeAdapter(Condition)
    raw = {
        "all": [
            {"fieldUuid": FIELD, "operator": "greater_than", "value": 18},
            {"not": {"fieldUuid": FIELD, "operator": "is_answered"}},
        ]
    }
    assert adapter.dump_python(adapter.validate_python(raw), mode="json", exclude_unset=True) == raw
    for raw in [
        {"fieldUuid": FIELD, "operator": "greater_than", "value": True},
        {"fieldUuid": FIELD, "operator": "less_than", "value": "not a date"},
        {"fieldUuid": FIELD, "operator": "equals", "value": {"anything": []}},
        {"fieldUuid": FIELD, "operator": "is_answered", "value": None},
        {"all": []},
    ]:
        with pytest.raises(ValidationError):
            adapter.validate_python(raw)
    dated = adapter.validate_python({"fieldUuid": FIELD, "operator": "less_than", "value": "2026-11-18"})
    assert dated.value == date(2026, 11, 18)


def test_submitted_answers_reject_arbitrary_json_and_preserve_matching_shape():
    for bad in [{"anything": [1, {"nested": True}]}, [1, 2], None]:
        with pytest.raises(ValidationError):
            AnsweredAnswer(state="answered", answer_spec={"type": "string", "required": True}, answer_value=bad)
    pair = {"prompt_uuid": FIELD, "match_uuid": "20000000-0000-4000-8000-000000000001"}
    matching = AnsweredAnswer(
        state="answered",
        answer_spec={"type": "object", "required": True, "valueType": "matching"},
        answer_value={"pairs": [pair]},
    )
    assert matching.model_dump(mode="json")["answer_value"] == {"pairs": [pair]}


def test_answer_bound_objects_are_typed_serialized_data():
    adapter = TypeAdapter(AnswerSpec)
    raw = {"type": "date", "required": True, "constraints": {"min": "2026-01-01", "max": "2026-12-31"}}
    assert adapter.dump_python(adapter.validate_python(raw), mode="json", exclude_unset=True) == raw
    for constraints in [{"min": "2026-02-30"}, {"min": 0}, {"min": "2026-12-31", "max": "2026-01-01"}]:
        with pytest.raises(ValidationError):
            adapter.validate_python(raw | {"constraints": constraints})
    with pytest.raises(ValidationError):
        adapter.validate_python({"type": "string", "required": True, "constraints": {"minLength": -1}})


def test_survey_models_have_no_raw_scalar_or_arbitrary_json_fields():
    root = Path(__file__).resolve().parents[3] / "app/schema/models/survey_document"
    for path in root.glob("*.py"):
        for cls in ast.parse(path.read_text()).body:
            if not isinstance(cls, ast.ClassDef):
                continue
            for field in cls.body:
                if isinstance(field, ast.AnnAssign):
                    names = {n.id for n in ast.walk(field.annotation) if isinstance(n, ast.Name)}
                    assert not names & {"str", "int", "JsonValue", "Any", "dict"}, (path, cls.name)
