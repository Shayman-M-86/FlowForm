"""Survey import preview composed from the canonical document model."""

from app.schema.api.common.base import APIResponseModel
from app.schema.models.survey_document.document import SurveyContent


class AIImportResponse(APIResponseModel):
    """Generated survey content before it is assigned to a persisted version."""

    definition: SurveyContent
