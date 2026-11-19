"""Pinned document fields supply result metadata without node-era copies."""

import pytest

from app.schema.models.survey_document import SurveyDefinition
from app.schema.models.survey_document.document import InputBlock
from app.schema.models.survey_document.fields import SingleChoiceInteraction
from app.services.admin_results.core.field_meta import build_field_map


def definition() -> SurveyDefinition:
    return SurveyDefinition.model_validate(
        {
            "id": "survey",
            "versionId": 7,
            "revision": 1,
            "title": "Survey",
            "projectName": "Project",
            "status": "published",
            "document": {
                "sections": [
                    {
                        "id": "section",
                        "title": "Section",
                        "blocks": [
                            {"id": "heading", "type": "heading", "content": {"text": "Heading", "level": 1}},
                            {
                                "id": "coffee",
                                "type": "input",
                                "field": {
                                    "id": "coffee_time",
                                    "uuid": "10000000-0000-4000-8000-000000000001",
                                    "prompt": "When did you drink coffee?",
                                    "interaction": {
                                        "kind": "single_choice",
                                        "options": [
                                            {
                                                "id": "morning",
                                                "uuid": "20000000-0000-4000-8000-000000000001",
                                                "label": "In the morning",
                                            }
                                        ],
                                    },
                                    "answerSpec": {"type": "choice", "required": True},
                                },
                            },
                        ],
                    }
                ]
            },
        }
    )


def test_field_index_keeps_pinned_wording_and_option_models():
    doc = definition()
    block = doc.document.sections[0].blocks[1]
    assert isinstance(block, InputBlock)
    fields = build_field_map(doc)
    assert len(fields) == 1
    field = fields[block.field.uuid]
    assert field is block.field
    assert field.id == "coffee_time" and field.prompt == "When did you drink coffee?"
    assert isinstance(field.interaction, SingleChoiceInteraction)
    assert field.interaction.options[0].label == "In the morning"
    assert field.answerSpec.type == "choice"


def test_absent_document_has_no_fabricated_metadata():
    assert build_field_map(None) == {}


def test_duplicate_field_uuid_is_not_silently_overwritten():
    doc = definition()
    section = doc.document.sections[0]
    section.blocks.append(section.blocks[1].model_copy(deep=True))
    with pytest.raises(ValueError, match="duplicate field UUID"):
        build_field_map(doc)
