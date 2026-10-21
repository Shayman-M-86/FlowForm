"""Field lookup and value parsing for results from a frozen survey document."""

from app.schema.api.content.survey_document import (
    InputBlock,
    SurveyDefinition,
    SurveyField,
)


def build_field_map(definition: SurveyDefinition) -> dict[str, SurveyField]:
    """Index fields in the session's published definition by answer identity."""
    return {
        block.field.id: block.field
        for section in definition.document.sections
        for block in section.blocks
        if isinstance(block, InputBlock)
    }
