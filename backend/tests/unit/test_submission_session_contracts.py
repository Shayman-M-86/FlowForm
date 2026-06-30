from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

import app.api.v1  # noqa: F401  (imported for @openapi_route registration side effect)
import app.openapi.registry as openapi_registry
from app.openapi.export import _build_minimal_spec_app
from app.openapi.spec import _explicit_methods, _flask_path_to_openapi, build_spec
from app.schema.api.requests.submission_sessions import (
    SaveSubmissionSessionAnswerRequest,
    StartSubmissionSessionRequest,
    SubmissionSessionEventRequest,
)
from app.schema.api.requests.survey_results import ExportSurveyResultsRequest, ListSubjectsRequest
from app.schema.api.responses.submission_sessions import StartSubmissionSessionResponse

# Snapshot the global @openapi_route registry at import time, once the v1 route
# decorators (loaded via ``import app.api.v1`` above) have populated it. Other
# suites (e.g. test_openapi_spec.py) clear the registry on teardown, so by the
# time a spec-building test here runs it may be empty depending on collection
# order. Restoring from this snapshot keeps the spec assertions order-independent
# without re-importing route modules (which would double-register blueprints).
_REGISTRY_SNAPSHOT = openapi_registry.get_registered_routes()


@pytest.fixture
def restored_openapi_registry() -> Iterator[None]:
    """Restore the captured @openapi_route registry for the duration of a test."""
    saved = openapi_registry.get_registered_routes()
    openapi_registry.clear_registry()
    openapi_registry._REGISTRY.extend(_REGISTRY_SNAPSHOT)
    try:
        yield
    finally:
        openapi_registry.clear_registry()
        openapi_registry._REGISTRY.extend(saved)


def test_start_submission_session_accepts_public_slug_access() -> None:
    payload = StartSubmissionSessionRequest.model_validate(
        {
            "access": {
                "type": "public_slug",
                "public_slug": "customer-intake",
            }
        }
    )

    assert payload.access.type == "public_slug"
    assert payload.access.public_slug == "customer-intake"


def test_start_submission_session_rejects_legacy_submission_fields() -> None:
    with pytest.raises(ValidationError) as exc_info:
        StartSubmissionSessionRequest.model_validate(
            {
                "access": {
                    "type": "public_slug",
                    "public_slug": "customer-intake",
                },
                "survey_version_id": 31,
                "started_at": "2026-06-11T01:20:00Z",
                "submitted_at": "2026-06-11T01:31:00Z",
                "answers": [],
                "metadata": {},
            }
        )

    fields = {error["loc"][0] for error in exc_info.value.errors()}
    assert {"survey_version_id", "started_at", "submitted_at", "answers", "metadata"} <= fields


def test_submission_session_response_contains_only_acknowledgement_fields() -> None:
    current = datetime.now(UTC)
    response = StartSubmissionSessionResponse(
        status="in_progress",
        started_at=current,
        expires_at=current,
        survey_version_id=31,
        subject_code="sub_test",
    )

    dumped = response.model_dump(mode="json")

    assert dumped == {
        "status": "in_progress",
        "started_at": current.isoformat().replace("+00:00", "Z"),
        "expires_at": current.isoformat().replace("+00:00", "Z"),
        "survey_version_id": 31,
        "subject_code": "sub_test",
    }
    assert "survey_schema" not in dumped
    assert "survey" not in dumped
    assert "version" not in dumped
    assert "compiled_schema" not in dumped
    assert "answers" not in dumped


def test_save_answer_rejects_body_question_identifier() -> None:
    with pytest.raises(ValidationError) as exc_info:
        SaveSubmissionSessionAnswerRequest.model_validate(
            {
                "question_node_id": "771ab5a1-462c-4c98-8fe5-dbc2c1939539",
                "client_mutation_id": "ce823b7d-5295-4ca6-bbb8-cfe367f28b31",
                "state": "answered",
                "answer_family": "rating",
                "answer_value": {"variant": "slider", "number": 8},
            }
        )

    assert exc_info.value.errors()[0]["loc"] == ("question_node_id",)


def test_save_answer_requires_answer_payload_when_answered() -> None:
    with pytest.raises(ValidationError) as exc_info:
        SaveSubmissionSessionAnswerRequest.model_validate(
            {
                "client_mutation_id": "ce823b7d-5295-4ca6-bbb8-cfe367f28b31",
                "state": "answered",
            }
        )

    assert "answer_family is required" in exc_info.value.errors()[0]["msg"]


def test_clear_answer_forbids_answer_payload() -> None:
    with pytest.raises(ValidationError) as exc_info:
        SaveSubmissionSessionAnswerRequest.model_validate(
            {
                "client_mutation_id": "b10063cb-9fb4-4ac2-b399-769f8781127f",
                "state": "cleared",
                "answer_family": "rating",
                "answer_value": {"variant": "slider", "number": 8},
            }
        )

    assert "answer_family must be omitted" in exc_info.value.errors()[0]["msg"]


def test_submission_session_paths_are_in_openapi_spec(restored_openapi_registry: None) -> None:
    app = _build_minimal_spec_app()
    spec = build_spec(app)
    paths = spec["paths"]

    assert sorted(paths["/api/v1/respondent/links/resolve"]) == ["post"]
    assert "post" in paths["/api/v1/respondent/submission-sessions"]
    assert "/api/v1/respondent/submission-sessions/current" not in paths
    assert "put" in paths["/api/v1/respondent/submission-sessions/current/answers/{question_node_id}"]
    assert "post" in paths["/api/v1/respondent/submission-sessions/current/events"]
    assert "post" in paths["/api/v1/respondent/submission-sessions/current/complete"]


def test_save_answer_accepts_client_mutation_uuid() -> None:
    payload = SaveSubmissionSessionAnswerRequest.model_validate(
        {
            "client_mutation_id": "ce823b7d-5295-4ca6-bbb8-cfe367f28b31",
            "state": "answered",
            "answer_family": "rating",
            "answer_value": {"variant": "slider", "number": 8},
        }
    )

    assert payload.client_mutation_id == UUID("ce823b7d-5295-4ca6-bbb8-cfe367f28b31")


def test_submission_session_event_accepts_question_viewed_event() -> None:
    payload = SubmissionSessionEventRequest.model_validate(
        {
            "event_type": "question_viewed",
            "question_node_id": "771ab5a1-462c-4c98-8fe5-dbc2c1939539",
        }
    )

    assert payload.event_type == "question_viewed"
    assert payload.question_node_id == UUID("771ab5a1-462c-4c98-8fe5-dbc2c1939539")


def test_list_subjects_request_applies_pagination_defaults() -> None:
    payload = ListSubjectsRequest.model_validate({})

    assert payload.page == 1
    assert payload.page_size == 20
    assert payload.include_decrypted_answer_values is False
    assert payload.include_events is False


def test_list_subjects_request_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ListSubjectsRequest.model_validate({"status": "not_a_status"})

    fields = {error["loc"][0] for error in exc_info.value.errors()}
    assert "status" in fields


def test_export_results_request_defaults_to_csv() -> None:
    payload = ExportSurveyResultsRequest.model_validate({})

    assert payload.format == "csv"
    assert payload.include_decrypted_answer_values is False
    assert payload.session_ids is None


def test_export_results_request_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ExportSurveyResultsRequest.model_validate({"format": "json", "survey_version_id": 3})

    fields = {error["loc"][0] for error in exc_info.value.errors()}
    assert "survey_version_id" in fields


def test_admin_results_paths_are_in_openapi_spec(restored_openapi_registry: None) -> None:
    app = _build_minimal_spec_app()
    spec = build_spec(app)
    paths = spec["paths"]

    base = "/api/v1/studio/projects/{project_id}/surveys/{survey_id}/results"
    assert "get" in paths[f"{base}/subjects"]
    assert "get" in paths[f"{base}/subjects/{{subject_id}}"]
    assert "post" in paths[f"{base}/export"]
    assert "delete" in paths[f"{base}/sessions/{{session_id}}"]


def test_openapi_export_covers_loaded_backend_routes(restored_openapi_registry: None) -> None:
    app = _build_minimal_spec_app()
    spec = build_spec(app)

    route_modules = {
        ".".join(path.with_suffix("").relative_to(Path(__file__).resolve().parents[2]).parts)
        for path in (Path(__file__).resolve().parents[2] / "app/api").rglob("*.py")
        if ".route(" in path.read_text(encoding="utf-8")
    }
    handler_modules = {view.__module__ for endpoint, view in app.view_functions.items() if endpoint != "static"}
    metadata_modules = {route.handler_qualname.rsplit(".", 1)[0] for route in openapi_registry.get_registered_routes()}

    assert route_modules <= handler_modules
    assert route_modules <= metadata_modules

    expected_operations: set[tuple[str, str]] = set()
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        openapi_path, _ = _flask_path_to_openapi(rule.rule)
        expected_operations.update((method.lower(), openapi_path) for method in _explicit_methods(rule))

    actual_operations = {
        (method, path)
        for path, path_item in spec["paths"].items()
        for method in path_item
    }

    assert actual_operations == expected_operations
