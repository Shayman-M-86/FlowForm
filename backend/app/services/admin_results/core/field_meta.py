"""Index existing field models from the response's pinned survey document."""

from app.schema.models.survey_document import SurveyContent
from app.schema.models.survey_document.document import InputBlock
from app.schema.models.survey_document.fields import SurveyField
from app.schema.types import SurveyFieldUuid

type FieldMap = dict[SurveyFieldUuid, SurveyField]


def build_field_map(content: SurveyContent | None) -> FieldMap:
    """Keep document field metadata without reconstructing a second shape."""
    fields: FieldMap = {}
    if content is None:
        return fields
    for section in content.sections:
        for block in section.blocks:
            if isinstance(block, InputBlock):
                field = block.field
                if field.uuid in fields:
                    raise ValueError("Pinned survey definition contains duplicate field UUIDs.")
                fields[field.uuid] = field
    return fields
