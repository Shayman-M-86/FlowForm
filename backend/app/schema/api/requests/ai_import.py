"""HTTP request for generating an editable survey draft."""

from app.schema.api.common.base import APIRequestModel
from app.schema.api.common.types import AIImportPrompt


class AIImportRequest(APIRequestModel):
    """Instructions for survey generation."""

    prompt: AIImportPrompt
