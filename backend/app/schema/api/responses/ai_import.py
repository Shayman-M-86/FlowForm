"""Survey import preview composed from the canonical document model."""

from app.schema.api.common.base import APIResponseModel
from app.schema.models.survey_document.document import SurveyDefinition


class AIImportResponse(APIResponseModel):
    """Generated survey definition for review and editing."""

    definition: SurveyDefinition
