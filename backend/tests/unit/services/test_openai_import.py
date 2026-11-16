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
        preview = OpenAIService().generate("Sleep habits", OpenAISettings(api_key_file=str(key_file)), user_key="1")
    assert preview.title == "Sleep habits"
    assert [node.content.family for node in preview.nodes] == ["field", "rating", "choice"]
    assert [node.sort_key for node in preview.nodes] == [1, 2, 3]
    assert len({node.id for node in preview.nodes}) == 3
    assert client_type.return_value.responses.parse.call_args.kwargs["store"] is False


def test_missing_key_returns_service_unavailable() -> None:
    with pytest.raises(AppError) as error:
        OpenAIService().generate("Sleep habits", OpenAISettings(), user_key="1")
    assert error.value.status_code == 503


def test_blank_prompt_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AIImportRequest(prompt="   ")


def test_requests_beyond_the_per_user_limit_are_rejected(tmp_path: Path) -> None:
    key_file = tmp_path / "key"
    key_file.write_text("test-key", encoding="utf-8")
    settings = OpenAISettings(api_key_file=str(key_file), rate_limit_max_requests=2, rate_limit_window_seconds=3600)
    service = OpenAIService()
    with patch("app.services.openai.OpenAI") as client_type:
        client_type.return_value.responses.parse.return_value = SimpleNamespace(output_parsed=None)
        for _ in range(2):
            with pytest.raises(AppError) as error:
                service.generate("Sleep habits", settings, user_key="1")
            assert error.value.status_code == 502  # failed generations still count
        with pytest.raises(AppError) as error:
            service.generate("Sleep habits", settings, user_key="1")
        assert error.value.status_code == 429
        assert error.value.code == "ai_import_rate_limited"
        assert client_type.return_value.responses.parse.call_count == 2

        # Other users keep their own allowance.
        with pytest.raises(AppError) as error:
            service.generate("Sleep habits", settings, user_key="2")
        assert error.value.status_code == 502


def test_unconfigured_requests_do_not_use_the_allowance() -> None:
    service = OpenAIService()
    settings = OpenAISettings(rate_limit_max_requests=1)
    for _ in range(3):
        with pytest.raises(AppError) as error:
            service.generate("Sleep habits", settings, user_key="1")
        assert error.value.status_code == 503
