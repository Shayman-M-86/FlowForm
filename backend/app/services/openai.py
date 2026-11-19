"""OpenAI-backed survey draft generation and conversion."""

import logging
import math
from uuid import uuid4

from openai import APIError, OpenAI
from pydantic import ValidationError

from app.core.config import OpenAISettings
from app.core.errors import AppError
from app.middleware.rate_limit.service import RateLimitConfig, RateLimitService
from app.schema.api.requests.content.ai_import import AIImportResponse, GeneratedQuestion, GeneratedSurvey
from app.schema.api.requests.content.node import CreateQuestionNodeRequest

logger = logging.getLogger(__name__)


class OpenAIService:
    """Generate a survey preview without changing stored survey content."""

    def __init__(self, settings: OpenAISettings) -> None:
        self._limiter: RateLimitService | None = None
        self._settings = settings

    def generate(self, prompt: str, user_key: str) -> AIImportResponse:
        """Call Structured Outputs and validate the resulting builder nodes."""
        try:
            api_key = self._settings.api_key
        except ValueError as exc:
            logger.error("OpenAI API key file is unavailable: %s", exc)
            raise AppError(503, "ai_import_unavailable", "Survey generation is not configured") from exc
        if api_key is None or not api_key.get_secret_value():
            raise AppError(503, "ai_import_unavailable", "Survey generation is not configured")
        self._check_rate_limit(user_key, self._settings)

        try:
            client = OpenAI(api_key=api_key.get_secret_value(), timeout=30.0, max_retries=1)
            response = client.responses.parse(
                model=self._settings.model,
                instructions=(
                    "Create a concise, neutral survey draft. Return 1 to 20 questions. "
                    "Use text, single_choice, multiple_choice, or rating. "
                    "Choice questions need 2 to 10 distinct options; other types need an empty options list. "
                    "Keep labels short and avoid personal or sensitive data requests unless explicitly asked."
                ),
                input=prompt,
                text_format=GeneratedSurvey,
                max_output_tokens=4000,
                store=False,
            )
        except (APIError, ValidationError) as exc:
            logger.warning("OpenAI survey generation failed: %s", type(exc).__name__)
            raise AppError(502, "ai_import_failed", "Survey generation failed") from exc

        generated = response.output_parsed
        if generated is None:
            raise AppError(502, "ai_import_failed", "Survey generation produced no draft")

        try:
            nodes = [self._to_node(question, index) for index, question in enumerate(generated.questions, start=1)]
            return AIImportResponse.model_validate(
                {"title": generated.title, "description": generated.description, "nodes": nodes}
            )
        except (ValidationError, ValueError) as exc:
            logger.warning("OpenAI survey draft failed FlowForm validation: %s", type(exc).__name__)
            raise AppError(502, "ai_import_invalid", "Generated survey does not meet builder rules") from exc

    def _check_rate_limit(self, user_key: str, settings: OpenAISettings) -> None:
        """Count every request that reaches OpenAI, including failed generations."""
        if self._limiter is None:
            self._limiter = RateLimitService(
                RateLimitConfig(
                    max_requests=settings.rate_limit_max_requests,
                    window_seconds=settings.rate_limit_window_seconds,
                )
            )
        decision = self._limiter.check(user_key)
        if not decision.allowed:
            minutes = math.ceil((decision.retry_after_seconds or 60) / 60)
            raise AppError(
                429,
                "ai_import_rate_limited",
                f"AI import limit reached. Try again in {minutes} minute{'s' if minutes != 1 else ''}.",
            )

    @staticmethod
    def _to_node(question: GeneratedQuestion, index: int) -> CreateQuestionNodeRequest:
        # Labels are trimmed and length-checked by the node schema; only rules it
        # does not cover are enforced here. Stray options on non-choice types are ignored.
        if question.type in {"single_choice", "multiple_choice"}:
            options = [option.strip() for option in question.options]
            if len(options) < 2 or len(set(options)) != len(options):
                raise ValueError("choice questions need at least two distinct options")
            content = {
                "family": "choice",
                "label": question.label,
                "definition": {
                    "min": 0,
                    "max": 1 if question.type == "single_choice" else len(options),
                    "options": [
                        {"id": f"option_{number}", "label": option} for number, option in enumerate(options, 1)
                    ],
                },
            }
        elif question.type == "text":
            content = {"family": "field", "label": question.label, "definition": {"field_type": "long_text"}}
        else:
            content = {
                "family": "rating",
                "label": question.label,
                "definition": {
                    "variant": "stars",
                    "stars": 5,
                    "ui": {"left_label": "Low", "right_label": "High"},
                },
            }
        node_id = uuid4()
        return CreateQuestionNodeRequest.model_validate(
            {
                "id": node_id,
                "node_key": f"ai_question_{node_id.hex}",
                "node_type": "question",
                "sort_key": index,
                "content": content,
            }
        )
