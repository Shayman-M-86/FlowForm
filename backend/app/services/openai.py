"""OpenAI survey generation and Flask service setup."""

import json
import logging
from typing import cast

from flask import Flask, current_app
from openai import APIError, OpenAI
from pydantic import ValidationError

from app.core.config import Settings
from app.domain.errors import SurveyGenerationFailedError, SurveyGenerationUnavailableError
from app.schema.models.survey_document.document import SurveyContent

logger = logging.getLogger(__name__)

EXTENSION_KEY = "openai_service"

# JSON mode accepts the canonical schema as instructions, including its
# discriminated unions and optional fields. Pydantic validates the result.
_GENERATION_INSTRUCTIONS = (
    "Generate a concise, neutral FlowForm survey as a JSON object using the schema below. "
    "Include at least one input block. Use unique readable IDs and distinct valid UUIDs "
    "for fields and options. Match each interaction with its answerSpec. "
    "Avoid collecting sensitive personal data unless explicitly requested.\n"
    + json.dumps(SurveyContent.model_json_schema(), separators=(",", ":"))
)


class OpenAIService:
    """Generate authored content for a survey preview."""

    def __init__(self, client: OpenAI | None, *, model: str) -> None:
        self._client = client
        self._model = model

    def generate(self, prompt: str) -> SurveyContent:
        """Generate and validate a complete draft."""
        client = self._client
        if client is None:
            raise SurveyGenerationUnavailableError()

        try:
            return self._request_draft(client, prompt)
        except (APIError, ValidationError) as exc:
            logger.warning("OpenAI survey generation failed (%s)", type(exc).__name__)
            # Provider and validation errors can contain generated content.
            raise SurveyGenerationFailedError() from None

    def _request_draft(self, client: OpenAI, prompt: str) -> SurveyContent:
        response = client.responses.create(
            model=self._model,
            instructions=_GENERATION_INSTRUCTIONS,
            input=prompt,
            text={"format": {"type": "json_object"}},
            max_output_tokens=4000,
            store=False,
        )
        if response.status != "completed" or not (output := response.output_text):
            logger.warning("OpenAI survey generation returned no complete draft (status=%s)", response.status)
            raise SurveyGenerationFailedError()

        return SurveyContent.model_validate_json(output)


class OpenAIServiceManager:
    """Initialize a shared generator for each Flask application."""

    def init_app(self, app: Flask) -> None:
        """Build the generator from the application's loaded settings."""
        settings: Settings = app.extensions["settings"]
        openai_settings = settings.flowform.openai

        client = None
        if openai_settings.api_key and (key := openai_settings.api_key.get_secret_value().strip()):
            client = OpenAI(api_key=key, timeout=30.0, max_retries=1)

        app.extensions[EXTENSION_KEY] = OpenAIService(client, model=openai_settings.model)


def get_openai_service() -> OpenAIService:
    """Return the generator registered on the current application."""
    return cast(OpenAIService, current_app.extensions[EXTENSION_KEY])
