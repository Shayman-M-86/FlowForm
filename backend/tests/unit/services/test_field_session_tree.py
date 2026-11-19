"""Admin projections preserve typed answers and never cross slot/field identities."""

import csv
import io
import json
from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from app.crypto._internal.errors import PayloadDecodeError
from app.crypto._internal.models import DecryptedAnswerPayload
from app.schema.api.responses.survey_results import SurveySessionTreeResponses
from app.schema.models.results.service_results import SessionTreeResult
from app.schema.orm.core.submission_answer_slot import SubmissionAnswerSlot
from app.schema.orm.core.submission_session import SubmissionSession
from app.schema.orm.core.survey import SurveyVersion
from app.schema.orm.response.response_answer import ResponseAnswer
from app.schema.types import (
    AnswerLocator,
    ProjectId,
    ResponseStoreId,
    SubmissionSessionId,
    SurveyFieldUuid,
    SurveyId,
    SurveyVersionId,
)
from app.services.admin_results.core import decryption, session_tree
from app.services.admin_results.core.decryption import ResolvedAnswers
from app.services.admin_results.core.export import format_export_file, to_export_rows
from app.services.admin_results.core.field_meta import build_field_map
from tests.unit.services.test_result_field_meta import definition


@pytest.fixture
def data():
    doc = definition()
    fields = build_field_map(doc)
    field = next(iter(fields.values()))
    session_id = TypeAdapter(SubmissionSessionId).validate_python(uuid4())
    version_id = TypeAdapter(SurveyVersionId).validate_python(7)
    slot = SubmissionAnswerSlot(
        submission_session_id=session_id, survey_version_id=version_id, field_uuid=field.uuid, field_id="stored_key"
    )
    slot.id = uuid4()
    locator = AnswerLocator(b"a" * 32)
    row = ResponseAnswer(answer_locator=locator, envelope_id=uuid4(), ciphertext=b"encrypted", nonce=b"n" * 12)
    version = SurveyVersion(survey_id=TypeAdapter(SurveyId).validate_python(1), version_number=1, definition=doc)
    version.id = version_id
    session = SubmissionSession(
        project_id=TypeAdapter(ProjectId).validate_python(1),
        survey_id=version.survey_id,
        survey_version_id=version_id,
        response_store_id=TypeAdapter(ResponseStoreId).validate_python(1),
        browser_session_token_hash=b"hash",
        linkage_key_version=1,
        expires_at=datetime(2030, 1, 1, tzinfo=UTC),
    )
    session.id = session_id
    session.survey_version = version
    return slot, locator, row, fields, session


def payload(field_uuid, state="answered", spec=None, value=None):
    data = {"v": 2, "field_uuid": field_uuid, "state": state}
    if state == "answered":
        data.update(
            answer_spec=spec or {"type": "string", "required": True}, answer_value="yes" if value is None else value
        )
    return TypeAdapter(DecryptedAnswerPayload).validate_python(data)


def result(data, decrypted=None, fields=None):
    slot, locator, row, indexed, _ = data
    return session_tree.build_answer_slot_result(
        slot,
        locator=locator,
        found={locator: row},
        decrypted_by_locator={locator: decrypted} if decrypted is not None else {},
        fields=indexed if fields is None else fields,
    )


def test_metadata_only_result_does_not_invent_plaintext(data):
    read = result(data)
    assert read.field_uuid == data[0].field_uuid and read.field_id == "coffee_time"
    assert read.field is data[3][data[0].field_uuid]
    assert read.has_encrypted_answer and not read.decrypted
    assert read.state is None and read.answer_value is None and read.answer_spec is None


def test_missing_document_field_keeps_slot_identity_and_self_describing_answer(data):
    read = result(data, payload(data[0].field_uuid), fields={})
    assert read.field is None and read.field_id == "stored_key"
    assert read.answer_spec is not None and read.answer_spec.type == "string"
    assert read.answer_value == "yes"


def test_decrypted_state_uses_submitted_spec_not_presentation_family(data):
    decrypted = payload(data[0].field_uuid, spec={"type": "integer", "required": True}, value=0)
    read = result(data, decrypted)
    assert read.state == "answered" and read.answer_value == 0
    assert read.answer_spec is decrypted.answer_spec
    assert read.field is not None and read.field.answerSpec.type == "choice"


def test_cleared_answer_has_no_value_or_invented_specification(data):
    read = result(data, payload(data[0].field_uuid, "cleared"))
    assert read.decrypted and read.state == "cleared"
    assert read.answer_value is None and read.answer_spec is None


def test_decrypted_field_identity_must_match_slot(data):
    other = TypeAdapter(SurveyFieldUuid).validate_python(uuid4())
    with pytest.raises(PayloadDecodeError, match="identity"):
        result(data, payload(other))


def test_tree_and_api_share_field_results_and_hide_internal_slot_ids(data, monkeypatch):
    slot, locator, row, fields, session = data
    resolved = ResolvedAnswers(
        locators={slot.id: locator}, found={locator: row}, decrypted_by_locator={locator: payload(slot.field_uuid)}
    )
    monkeypatch.setattr(session_tree.submission_answer_slots, "list_by_session", Mock(return_value=[slot]))
    resolve = Mock(return_value=resolved)
    monkeypatch.setattr(session_tree, "resolve_and_decrypt_answers", resolve)
    builder = session_tree.SessionTreeBuilder(cache=Mock(), clients=Mock())
    tree = builder.build_session_result(
        Mock(spec=Session),
        Mock(spec=Session),
        session=session,
        include_decrypted_answer_values=True,
        include_events=False,
    )
    response = SurveySessionTreeResponses.model_validate(tree)
    body = response.model_dump(mode="json")
    assert body["answers"][0]["field_uuid"] == str(slot.field_uuid)
    assert body["answers"][0]["state"] == "answered" and body["answers"][0]["answer_spec"]["type"] == "string"
    assert "slot_id" not in body["answers"][0] and "question_node_id" not in body["answers"][0]
    assert tree.answers[0].field is fields[slot.field_uuid]


def test_events_use_field_uuid_and_remain_optional(data, monkeypatch):
    session = data[4]
    event = Mock(event_type="field_viewed", field_uuid=data[0].field_uuid, received_at=datetime(2020, 1, 1, tzinfo=UTC))
    fetch = Mock(return_value=[event])
    monkeypatch.setattr(session_tree.submission_events, "list_by_session", fetch)
    builder = session_tree.SessionTreeBuilder(cache=Mock(), clients=Mock())
    events = builder.load_events(Mock(spec=Session), session=session)
    assert events is not None and events[0].field_uuid == data[0].field_uuid
    fetch.side_effect = RuntimeError("analytics unavailable")
    assert builder.load_events(Mock(spec=Session), session=session) is None


@pytest.mark.parametrize(
    ("spec", "selected"),
    [
        ({"type": "choice_set", "required": True}, ["20000000-0000-4000-8000-000000000001"]),
        ({"type": "date", "required": True}, "2020-01-01"),
        (
            {"type": "object", "valueType": "matching", "required": True},
            {
                "pairs": [
                    {
                        "prompt_uuid": "30000000-0000-4000-8000-000000000001",
                        "match_uuid": "40000000-0000-4000-8000-000000000001",
                    }
                ]
            },
        ),
    ],
)
def test_json_and_csv_exports_use_typed_spec_and_json_safe_values(data, spec, selected):
    read = result(data, payload(data[0].field_uuid, spec=spec, value=selected))
    rows = to_export_rows(SessionTreeResult(session=data[4], answers=[read]))
    survey_id = TypeAdapter(SurveyId).validate_python(1)
    exported = json.loads(format_export_file(rows, export_format="json", survey_id=survey_id).body)[0]
    assert exported["field_uuid"] == str(data[0].field_uuid) and exported["field_id"] == "coffee_time"
    assert exported["answer_spec"]["type"] == spec["type"] and exported["answer_value"] == selected
    csv_row = next(csv.DictReader(io.StringIO(format_export_file(rows, export_format="csv", survey_id=survey_id).body)))
    assert json.loads(csv_row["answer_spec"])["type"] == spec["type"]
    actual = json.loads(csv_row["answer_value"]) if isinstance(selected, (dict, list)) else csv_row["answer_value"]
    assert actual == selected
    assert "question_key" not in csv_row and "answer_family" not in csv_row


def test_metadata_only_resolution_never_loads_session_key_or_decrypts(data, monkeypatch):
    slot, locator, row, _, session = data
    monkeypatch.setattr(decryption, "resolve_answer_locators", Mock(return_value={slot.id: locator}))
    monkeypatch.setattr(decryption.response_answer_repo, "get_by_locators", Mock(return_value=[row]))
    load = Mock(side_effect=AssertionError("metadata-only request must not load the session key"))
    decrypt = Mock(side_effect=AssertionError("metadata-only request must not decrypt"))
    monkeypatch.setattr(decryption, "load_session_envelope_crypto_context", load)
    monkeypatch.setattr(decryption, "decrypt_answer_current", decrypt)
    resolved = decryption.resolve_and_decrypt_answers(
        Mock(spec=Session),
        Mock(spec=Session),
        session=session,
        slots=[slot],
        include_decrypted_answer_values=False,
        cache=Mock(),
        clients=Mock(),
    )
    assert resolved.found == {locator: row} and resolved.decrypted_by_locator == {}
    load.assert_not_called()
    decrypt.assert_not_called()


def test_api_projection_preserves_long_form_answer_limit(data):
    read = result(data, payload(data[0].field_uuid, value="x" * 4000))
    response = SurveySessionTreeResponses.model_validate(SessionTreeResult(session=data[4], answers=[read]))
    value = response.answers[0].answer_value
    assert isinstance(value, str) and len(value) == 4000
