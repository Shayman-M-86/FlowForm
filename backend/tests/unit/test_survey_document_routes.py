"""HTTP contracts at the document service boundaries."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from flask import Flask, g

import app.api.v1.respondent.submission_sessions as respondent
import app.api.v1.studio.surveys.versions as versions
import app.services.access.access_service as access
from app.api.utils.errors import register_error_handlers
from app.api.v1.respondent import respondent_bp
from app.api.v1.studio.projects import studio_projects_bp
from app.core.extensions import auth
from app.domain.errors import FieldNotInDefinitionError, InvalidFieldAnswerError, VersionNotEditableError
from app.middleware.url_converters import register_url_converters
from app.schema.api.content.survey_document import SurveyDefinition
from app.services.results import AnswerSaveResult
from tests.survey_document import make_definition

_BASE = "/api/v1/studio/projects/1/surveys/2/versions"
_ANSWER = "/api/v1/respondent/submission-sessions/current/answers/field_name"


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> Flask:
    flask_app = Flask(__name__)
    flask_app.config["TESTING"] = True
    register_url_converters(flask_app)
    register_error_handlers(flask_app)
    flask_app.register_blueprint(studio_projects_bp, url_prefix="/api/v1/studio/projects")
    flask_app.register_blueprint(respondent_bp, url_prefix="/api/v1/respondent")
    monkeypatch.setattr(auth, "_extract_bearer_token", lambda: "token")
    monkeypatch.setattr(auth, "_verify_access_token", lambda _token: {"sub": "auth0|test"})
    for module in (versions, respondent):
        monkeypatch.setattr(module, "get_core_db", lambda: Mock())
    monkeypatch.setattr(respondent, "get_response_db", lambda: Mock())
    monkeypatch.setattr(respondent, "get_submission_session_token", lambda: "session-token")

    @flask_app.before_request
    def actor() -> None:
        g.actor = SimpleNamespace(id=1, platform_admin=True)

    return flask_app


def _version() -> SimpleNamespace:
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=3,
        survey_id=2,
        version_number=1,
        revision=1,
        status="draft",
        definition=make_definition(),
        published_at=None,
        created_by_user_id=1,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.parametrize(
    "method,suffix,service_name,status",
    [
        ("POST", "", "create_version", 201),
        ("PUT", "/1/definition", "replace_definition", 200),
    ],
)
def test_version_routes_pass_validated_definition(app, monkeypatch, method, suffix, service_name, status) -> None:
    service = Mock(return_value=_version())
    monkeypatch.setattr(versions.survey_service, service_name, service)
    response = app.test_client().open(_BASE + suffix, method=method, json={"definition": make_definition()})
    assert response.status_code == status
    assert isinstance(service.call_args.kwargs["definition"], SurveyDefinition)
    assert response.json["revision"] == 1
    assert "definition" in response.json


def test_replace_published_definition_uses_existing_error(app, monkeypatch) -> None:
    monkeypatch.setattr(
        versions.survey_service, "replace_definition", Mock(side_effect=VersionNotEditableError(status="published"))
    )
    response = app.test_client().put(_BASE + "/1/definition", json={"definition": make_definition()})
    assert response.status_code == 409


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("PUT", _BASE + "/1/definition", {"definition": make_definition()}),
        ("GET", "/api/v1/studio/projects/1/surveys/2/results/subjects", None),
    ],
)
def test_document_and_results_routes_require_survey_permissions(app, monkeypatch, method, path, body) -> None:
    @app.before_request
    def non_admin() -> None:
        g.actor = SimpleNamespace(id=1, platform_admin=False)

    monkeypatch.setattr(access, "get_core_db", lambda: Mock())
    monkeypatch.setattr(
        access.access_service,
        "get_survey_access",
        Mock(return_value=SimpleNamespace(membership=object(), permissions=set())),
    )
    response = app.test_client().open(path, method=method, json=body)
    assert response.status_code == 403


def test_invalid_document_error_paths_match_request_properties(app) -> None:
    definition = make_definition()
    definition["document"]["sections"][0]["blocks"] = [
        {"id": "block_explanation", "type": "paragraph", "content": {"text": ""}}
    ]
    response = app.test_client().post(_BASE, json={"definition": definition})
    assert response.status_code == 422
    assert response.json["details"]["errors"][0]["field"] == "definition.document.sections.0.blocks.0.content.text"


def test_document_error_paths_preserve_the_real_field_property(app) -> None:
    definition = make_definition()
    definition["document"]["sections"][0]["blocks"][0]["field"]["prompt"] = ""
    response = app.test_client().post(_BASE, json={"definition": definition})
    assert response.status_code == 422
    assert response.json["details"]["errors"][0]["field"] == "definition.document.sections.0.blocks.0.field.prompt"


def test_results_query_validation_uses_the_request_error_envelope(app) -> None:
    response = app.test_client().get("/api/v1/studio/projects/1/surveys/2/results/subjects?page=0")
    assert response.status_code == 422
    assert response.json["code"] == "VALIDATION_ERROR"
    assert response.json["details"]["errors"][0]["field"] == "page"


def test_answer_route_uses_trusted_response_type_and_normalized_value(app, monkeypatch) -> None:
    save = Mock(return_value=AnswerSaveResult(field_key="name", response_type="string", value="Alice"))
    monkeypatch.setattr(respondent.session_management_service, "save_answer", save)
    mutation = str(uuid4())
    response = app.test_client().put(
        _ANSWER, json={"state": "answered", "value": "Alice", "client_mutation_id": mutation}
    )
    assert response.status_code == 200
    assert response.json["field_id"] == "field_name"
    assert response.json["response_type"] == "string"
    assert response.json["value"] == "Alice"
    assert save.call_args.kwargs["field_id"] == "field_name"


@pytest.mark.parametrize("error", [FieldNotInDefinitionError(), InvalidFieldAnswerError()])
def test_answer_domain_errors_keep_the_existing_envelope(app, monkeypatch, error) -> None:
    monkeypatch.setattr(respondent.session_management_service, "save_answer", Mock(side_effect=error))
    response = app.test_client().put(
        _ANSWER, json={"state": "answered", "value": "Alice", "client_mutation_id": str(uuid4())}
    )
    assert response.status_code == 400
    assert response.json["code"] == error.code


def test_field_viewed_event_calls_field_service(app, monkeypatch) -> None:
    record = Mock()
    monkeypatch.setattr(respondent.session_management_service, "record_field_viewed", record)
    response = app.test_client().post(
        "/api/v1/respondent/submission-sessions/current/events",
        json={"event_type": "field_viewed", "field_id": "field_name"},
    )
    assert response.status_code == 204
    assert record.call_args.kwargs["field_id"] == "field_name"
