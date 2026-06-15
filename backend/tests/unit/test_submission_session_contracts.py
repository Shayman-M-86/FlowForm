from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

import app.api.v1  # noqa: F401  (imported for @openapi_route registration side effect)
import app.openapi.registry as openapi_registry
from app.openapi.export import _build_minimal_spec_app
from app.openapi.spec import build_spec
from app.schema.api.requests.submission_sessions import (
    SaveSubmissionSessionAnswerRequest,
    StartSubmissionSessionRequest,
    SubmissionSessionEventRequest,
)
from app.schema.api.requests.survey_responses import ExportSurveyResponsesRequest, ListSurveyResponsesRequest
from app.schema.api.responses.submission_sessions import PublicSubmissionSessionResponses

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


def test_submission_session_response_omits_survey_schema_and_answers() -> None:
    current = datetime.now(UTC)
    response = PublicSubmissionSessionResponses(
        status="in_progress",
        started_at=current,
        expires_at=current,
        survey_version_id=31,
    )

    dumped = response.model_dump(mode="json")

    assert dumped == {
        "status": "in_progress",
        "started_at": current.isoformat().replace("+00:00", "Z"),
        "expires_at": current.isoformat().replace("+00:00", "Z"),
        "survey_version_id": 31,
    }
    assert "survey" not in dumped
    assert "version" not in dumped
    assert "compiled_schema" not in dumped
    assert "answers" not in dumped


def test_save_answer_requires_body_question_identifier() -> None:
    with pytest.raises(ValidationError) as exc_info:
        SaveSubmissionSessionAnswerRequest.model_validate(
            {
                "client_mutation_id": "ce823b7d-5295-4ca6-bbb8-cfe367f28b31",
                "state": "answered",
                "answer_family": "rating",
                "answer_value": {"value": 8},
            }
        )

    assert exc_info.value.errors()[0]["loc"] == ("question_node_id",)


def test_save_answer_requires_answer_payload_when_answered() -> None:
    with pytest.raises(ValidationError) as exc_info:
        SaveSubmissionSessionAnswerRequest.model_validate(
            {
                "question_node_id": "771ab5a1-462c-4c98-8fe5-dbc2c1939539",
                "client_mutation_id": "ce823b7d-5295-4ca6-bbb8-cfe367f28b31",
                "state": "answered",
            }
        )

    assert "answer_family is required" in exc_info.value.errors()[0]["msg"]


def test_clear_answer_forbids_answer_payload() -> None:
    with pytest.raises(ValidationError) as exc_info:
        SaveSubmissionSessionAnswerRequest.model_validate(
            {
                "question_node_id": "771ab5a1-462c-4c98-8fe5-dbc2c1939539",
                "client_mutation_id": "b10063cb-9fb4-4ac2-b399-769f8781127f",
                "state": "cleared",
                "answer_family": "rating",
                "answer_value": {"value": 8},
            }
        )

    assert "answer_family must be omitted" in exc_info.value.errors()[0]["msg"]


def test_submission_session_paths_are_in_openapi_spec(restored_openapi_registry: None) -> None:
    app = _build_minimal_spec_app()
    spec = build_spec(app)
    paths = spec["paths"]

    assert sorted(paths["/api/v1/public/links/resolve"]) == ["post"]
    assert "post" in paths["/api/v1/public/submission-session/start"]
    assert "/api/v1/public/submission-sessions/current" not in paths
    assert "put" in paths["/api/v1/public/submission-session/answer"]
    assert "post" in paths["/api/v1/public/submission-session/event"]
    assert "post" in paths["/api/v1/public/submission-session/complete"]


def test_save_answer_accepts_client_mutation_uuid() -> None:
    payload = SaveSubmissionSessionAnswerRequest.model_validate(
        {
            "question_node_id": "771ab5a1-462c-4c98-8fe5-dbc2c1939539",
            "client_mutation_id": "ce823b7d-5295-4ca6-bbb8-cfe367f28b31",
            "state": "answered",
            "answer_family": "rating",
            "answer_value": {"value": 8},
        }
    )

    assert payload.client_mutation_id == UUID("ce823b7d-5295-4ca6-bbb8-cfe367f28b31")
    assert payload.question_node_id == UUID("771ab5a1-462c-4c98-8fe5-dbc2c1939539")


def test_submission_session_event_accepts_question_viewed_event() -> None:
    payload = SubmissionSessionEventRequest.model_validate(
        {
            "event_type": "question_viewed",
            "question_node_id": "771ab5a1-462c-4c98-8fe5-dbc2c1939539",
        }
    )

    assert payload.event_type == "question_viewed"
    assert payload.question_node_id == UUID("771ab5a1-462c-4c98-8fe5-dbc2c1939539")


def test_list_responses_request_applies_pagination_defaults() -> None:
    payload = ListSurveyResponsesRequest.model_validate({})

    assert payload.page == 1
    assert payload.page_size == 20
    assert payload.status is None


def test_list_responses_request_rejects_unknown_status() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ListSurveyResponsesRequest.model_validate({"status": "not_a_status"})

    assert exc_info.value.errors()[0]["loc"] == ("status",)


def test_export_responses_request_defaults_to_csv() -> None:
    payload = ExportSurveyResponsesRequest.model_validate({})

    assert payload.format == "csv"
    assert payload.include_history is False
    assert payload.session_ids is None


def test_export_responses_request_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ExportSurveyResponsesRequest.model_validate({"format": "json", "survey_version_id": 3})

    fields = {error["loc"][0] for error in exc_info.value.errors()}
    assert "survey_version_id" in fields


def test_admin_response_paths_are_in_openapi_spec(restored_openapi_registry: None) -> None:
    app = _build_minimal_spec_app()
    spec = build_spec(app)
    paths = spec["paths"]

    base = "/api/v1/projects/{project_id}/surveys/{survey_id}/responses"
    assert "get" in paths[base]
    assert "post" in paths[f"{base}/export"]
    assert "get" in paths[f"{base}/{{session_id}}"]
    assert "delete" in paths[f"{base}/{{session_id}}"]
    assert "get" in paths[f"{base}/{{session_id}}/history"]
