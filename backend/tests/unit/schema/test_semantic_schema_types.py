"""Shared semantic types across document, request, and response boundaries."""

import ast
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import TypeAdapter, ValidationError

from app.schema.api.requests.submission_sessions import SaveSubmissionSessionAnswerRequest
from app.schema.api.responses.submission_sessions.answers import SavedAnsweredResponse, SavedClearedResponse
from app.schema.models.common.types import Timestamp
from app.schema.models.projects.types import ProjectMembershipId, ProjectRoleId
from app.schema.models.submission.types import ClientMutationId
from app.schema.models.survey.fields import SurveyField
from app.schema.models.survey.types import SurveyFieldUuid

FIELD = "10000000-0000-4000-8000-000000000001"
MUTATION = "60000000-0000-4000-8000-000000000001"


@pytest.mark.parametrize("value_type", [SurveyFieldUuid, ClientMutationId])
def test_uuid_types_preserve_wire_format(value_type):
    adapter = TypeAdapter(value_type)
    assert adapter.validate_python(FIELD) == UUID(FIELD)
    assert json.loads(adapter.dump_json(UUID(FIELD))) == FIELD
    assert adapter.json_schema()["format"] == "uuid"
    with pytest.raises(ValidationError):
        adapter.validate_python("not-a-uuid")


@pytest.mark.parametrize("state", ["answered", "cleared"])
def test_answer_request_and_response_share_identity_types(state):
    raw = {"field_uuid": FIELD, "client_mutation_id": MUTATION, "state": state}
    if state == "answered":
        raw.update(answer_spec={"type": "integer", "required": True}, answer_value=24)
    request = TypeAdapter(SaveSubmissionSessionAnswerRequest).validate_python(raw)
    response_type = SavedAnsweredResponse if state == "answered" else SavedClearedResponse
    recorded = datetime(2020, 1, 1, tzinfo=UTC)
    response = response_type.model_validate(request.model_dump() | {"saved_at": recorded})
    assert response.field_uuid == request.field_uuid
    assert response.client_mutation_id == request.client_mutation_id
    assert response.saved_at == recorded
    assert json.loads(response.model_dump_json())["field_uuid"] == FIELD


def test_document_and_answer_reference_the_same_field_identity():
    field = SurveyField.model_validate(
        {
            "id": "age",
            "uuid": FIELD,
            "prompt": "Age?",
            "interaction": {"kind": "number"},
            "answerSpec": {"type": "integer", "required": True},
        }
    )
    assert field.uuid == TypeAdapter(SurveyFieldUuid).validate_python(FIELD)


@pytest.mark.parametrize("value_type", [ProjectRoleId, ProjectMembershipId])
def test_role_and_membership_ids_match_bigint_storage(value_type):
    adapter = TypeAdapter(value_type)
    assert adapter.validate_python(2**31) == 2**31
    assert adapter.validate_python(2**63 - 1) == 2**63 - 1
    for invalid in [0, -1, 2**63]:
        with pytest.raises(ValidationError):
            adapter.validate_python(invalid)


def test_timestamp_preserves_source_value():
    recorded = datetime(2020, 1, 1, tzinfo=UTC)
    assert TypeAdapter(Timestamp).validate_python(recorded) == recorded
    with pytest.raises(ValidationError):
        SavedClearedResponse(field_uuid=FIELD, client_mutation_id=MUTATION)


def test_api_models_use_named_value_types():
    root = Path(__file__).resolve().parents[3] / "app/schema/api"
    for folder in [root / "requests", root / "responses"]:
        for path in folder.rglob("*.py"):
            for cls in ast.parse(path.read_text()).body:
                if not isinstance(cls, ast.ClassDef):
                    continue
                for field in cls.body:
                    if not isinstance(field, ast.AnnAssign):
                        continue
                    names = {n.id for n in ast.walk(field.annotation) if isinstance(n, ast.Name)}
                    assert not names & {"str", "int", "UUID", "datetime"}, (path, cls.name, field.target)
                    if isinstance(field.value, ast.Call):
                        assert all(
                            k.arg
                            in {
                                "default",
                                "default_factory",
                                "alias",
                                "validation_alias",
                                "serialization_alias",
                                "description",
                            }
                            for k in field.value.keywords
                        ), (path, cls.name)
