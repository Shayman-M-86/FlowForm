from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.core.config import OpenAISettings
from app.core.errors import AppError
from app.schema.api.requests.content.ai_import import AIImportRequest, GeneratedSurvey
from app.services.openai import OpenAIService


def test_generated_preview_is_valid_builder_content(tmp_path: Path) -> None:
    key_file = tmp_path / "key"
    key_file.write_text("test-key", encoding="utf-8")
    generated = GeneratedSurvey.model_validate(
        {
            "title": "Sleep habits",
            "description": "Student sleep survey",
            "questions": [
                {"label": "How long do you sleep?", "type": "text", "options": []},
                {"label": "How rested do you feel?", "type": "rating", "options": []},
                {"label": "When do you drink coffee?", "type": "multiple_choice", "options": ["Morning", "Evening"]},
            ],
        }
    )
    with patch("app.services.openai.OpenAI") as client_type:
        client_type.return_value.responses.parse.return_value = SimpleNamespace(output_parsed=generated)
        preview = OpenAIService().generate("Sleep habits", OpenAISettings(api_key_file=str(key_file)))
    assert preview.title == "Sleep habits"
    assert [node.content.family for node in preview.nodes] == ["field", "rating", "choice"]
    assert [node.sort_key for node in preview.nodes] == [1, 2, 3]
    assert len({node.id for node in preview.nodes}) == 3
    assert client_type.return_value.responses.parse.call_args.kwargs["store"] is False


def test_missing_key_returns_service_unavailable() -> None:
    with pytest.raises(AppError) as error:
        OpenAIService().generate("Sleep habits", OpenAISettings())
    assert error.value.status_code == 503


def test_blank_prompt_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AIImportRequest(prompt="   ")
