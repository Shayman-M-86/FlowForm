from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from flask import Flask
from httpx import Request
from openai import APIConnectionError, OpenAI
from pydantic import ValidationError

from app.core.config import OpenAISettings
from app.core.extensions import openai_service_manager
from app.domain.errors import SurveyGenerationFailedError, SurveyGenerationUnavailableError
from app.schema.api.requests.ai_import import AIImportRequest
from app.schema.models.survey_document.document import InputBlock
from app.services.openai import OpenAIService, get_openai_service

_GENERATED_JSON = """{
    "title": "Sleep habits",
    "document": {
        "sections": [{
            "id": "habits",
            "title": "Habits",
            "blocks": [{
                "id": "sleep",
                "type": "input",
                "field": {
                    "id": "sleep_hours",
                    "uuid": "7c283418-01c8-422d-ba30-2f905b2db70f",
                    "prompt": "How many hours do you sleep?",
                    "interaction": {"kind": "number"},
                    "answerSpec": {"type": "integer", "required": true, "constraints": {"min": 0, "max": 24}}
                }
            }]
        }]
    }
}"""


def test_application_reuses_configured_generator(tmp_path: Path) -> None:
    key_file = tmp_path / "key"
    key_file.write_text("test-key\n", encoding="utf-8")
    settings = OpenAISettings(api_key_file=str(key_file), model="test-model")
    key_file.unlink()

    app = Flask(__name__)
    app.extensions["settings"] = SimpleNamespace(flowform=SimpleNamespace(openai=settings))
    disabled = Flask("disabled")
    disabled.extensions["settings"] = SimpleNamespace(flowform=SimpleNamespace(openai=OpenAISettings()))
    with patch("app.services.openai.OpenAI") as client_type:
        create = client_type.return_value.responses.create
        create.return_value = SimpleNamespace(status="completed", output_text=_GENERATED_JSON)
        openai_service_manager.init_app(app)
        openai_service_manager.init_app(disabled)
        with disabled.app_context():
            with pytest.raises(SurveyGenerationUnavailableError) as error:
                get_openai_service().generate("Sleep habits")
            assert (error.value.status_code, error.value.code) == (503, "HTTP_503")
            create.assert_not_called()
        with app.app_context():
            generator = get_openai_service()
            for _ in range(2):
                content = generator.generate("Sleep habits")
                assert content.title == "Sleep habits"
                block = content.document.sections[0].blocks[0]
                assert isinstance(block, InputBlock)
                assert block.field.answerSpec.type == "integer"
        client_type.assert_called_once_with(api_key="test-key", timeout=30.0, max_retries=1)
        assert create.call_count == 2
        assert create.call_args.kwargs["model"] == "test-model"
        assert create.call_args.kwargs["store"] is False


@pytest.mark.parametrize(
    ("status", "output_text"),
    [
        ("completed", ""),
        ("incomplete", _GENERATED_JSON),
        ("completed", '{"title": "Sleep habits", "nodes": []}'),
        ("completed", _GENERATED_JSON.replace('"max": 24', '"max": -1')),
    ],
)
def test_unusable_generation_raises_upstream_error(status: str, output_text: str) -> None:
    client = Mock(spec=OpenAI, responses=Mock())
    client.responses.create.return_value = SimpleNamespace(status=status, output_text=output_text)
    with pytest.raises(SurveyGenerationFailedError) as error:
        OpenAIService(client, model="test-model").generate("Sleep habits")
    assert (error.value.status_code, error.value.code) == (502, "HTTP_502")


def test_provider_failure_raises_upstream_error() -> None:
    client = Mock(spec=OpenAI, responses=Mock())
    client.responses.create.side_effect = APIConnectionError(request=Request("POST", "https://example.test/"))
    with pytest.raises(SurveyGenerationFailedError) as error:
        OpenAIService(client, model="test-model").generate("Sleep habits")
    assert (error.value.status_code, error.value.code) == (502, "HTTP_502")


def test_blank_prompt_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AIImportRequest(prompt="   ")
