"""Field identity, optional decryption, and document-answer export contracts."""

import json
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from app.crypto._internal.models import DecryptedAnswerPayload
from app.crypto.models import AnswerLocator
from app.schema.api.content.survey_document import SurveyDefinition, SurveyField
from app.schema.api.responses.survey_results import SurveySessionTreeResponses
from app.schema.orm.core.submission_answer_slot import SubmissionAnswerSlot
from app.schema.orm.core.submission_session import SubmissionSession
from app.services.admin_results.core.export import format_export_file, to_export_rows
from app.services.admin_results.core.field_meta import build_field_map
from app.services.admin_results.core.session_tree import build_answer_slot_result
from app.services.results import SessionTreeResult
from tests.survey_document import make_definition


def _field() -> SurveyField:
    definition = make_definition()
    definition["document"]["sections"][0]["blocks"][0]["field"].update(
        interaction={"kind": "date"}, response={"type": "date"}
    )
    return build_field_map(SurveyDefinition.model_validate(definition))["field_name"]


@pytest.mark.parametrize("state,value", [("answered", "2026-10-21"), ("cleared", None)])
def test_results_and_exports_preserve_field_answer_shape(state, value) -> None:
    slot = SubmissionAnswerSlot(id=uuid4(), field_id="field_name")
    locator = AnswerLocator(b"a" * 32)
    payload = DecryptedAnswerPayload(field_id="field_name", answer_state=state, answer_value=value)
    answer = build_answer_slot_result(
        slot, locator=locator, found={locator: object()}, decrypted_by_locator={locator: payload}, field=_field()
    )
    now = datetime.now(UTC)
    session = SubmissionSession(
        id=uuid4(),
        survey_id=1,
        survey_version_id=2,
        session_status="completed",
        started_at=now,
        completed_at=now,
        last_activity_at=now,
    )
    tree = SessionTreeResult(session=session, answers=[answer])
    response = SurveySessionTreeResponses.model_validate(tree)
    assert response.model_dump(mode="json")["answers"][0]["answer_value"] == value
    assert answer.field_key == "name"
    assert answer.response_type == "date"
    assert answer.answer_value == (date(2026, 10, 21) if value else None)
    exported = format_export_file(to_export_rows(tree), export_format="json", survey_id=1)
    row = json.loads(exported.body)[0]
    assert row["field_id"] == "field_name"
    assert row["answer_value"] == value
    assert "question_key" not in row


def test_metadata_results_do_not_expose_encrypted_or_plaintext_values() -> None:
    slot = SubmissionAnswerSlot(id=uuid4(), field_id="field_name")
    locator = AnswerLocator(b"a" * 32)
    result = build_answer_slot_result(
        slot, locator=locator, found={locator: object()}, decrypted_by_locator={}, field=_field()
    )
    assert result.has_encrypted_answer
    assert not result.decrypted
    assert result.answer_state is None
    assert result.answer_value is None


def test_decrypted_field_must_match_the_answer_slot() -> None:
    slot = SubmissionAnswerSlot(id=uuid4(), field_id="field_name")
    locator = AnswerLocator(b"a" * 32)
    payload = DecryptedAnswerPayload(field_id="field_other", answer_state="answered", answer_value="2026-10-21")
    with pytest.raises(ValueError, match="does not match"):
        build_answer_slot_result(
            slot, locator=locator, found={locator: object()}, decrypted_by_locator={locator: payload}, field=_field()
        )
