"""Small canonical survey definitions shared by migration tests."""

from typing import Any

from app.schema.api.content.survey_document import SurveyDefinition


def make_definition() -> dict[str, Any]:
    """Return a fresh complete document with one text field."""
    return SurveyDefinition.model_validate(
        {
            "schemaVersion": 1,
            "document": {
                "sections": [
                    {
                        "id": "section_intro",
                        "title": "Introduction",
                        "blocks": [
                            {
                                "id": "block_name",
                                "type": "input",
                                "field": {
                                    "id": "field_name",
                                    "key": "name",
                                    "prompt": "Your name?",
                                    "interaction": {"kind": "text"},
                                    "response": {"type": "string"},
                                },
                            }
                        ],
                    }
                ],
            },
        }
    ).model_dump(by_alias=True, mode="json")
