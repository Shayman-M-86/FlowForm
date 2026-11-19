"""A field slot binds a pinned document field to one stable encrypted answer."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, create_autospec
from uuid import uuid4

import pytest
from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from app.crypto.answers import decrypt_answer_current
from app.crypto.models import AnswerContext, LinkageKey, PlaintextSessionKey, SubmissionSessionContext
from app.domain.errors import AnswerSaveError, FieldNotInVersionError, SessionInvalidError
from app.schema.models.survey_document import SurveyDefinition
from app.schema.models.survey_document.answers import AnswerData
from app.schema.orm.core.submission_answer_slot import SubmissionAnswerSlot
from app.schema.orm.core.submission_session import SubmissionSession
from app.schema.orm.core.survey import SurveyVersion
from app.schema.types import (
    ClientMutationId,
    ProjectId,
    ResponseStoreId,
    SessionLocator,
    SubmissionSessionId,
    SurveyFieldUuid,
    SurveyId,
    SurveyVersionId,
)
from app.services.public_submissions.core.actions import answer_save as module


@pytest.fixture
def setup(monkeypatch):
    project_id = TypeAdapter(ProjectId).validate_python(1)
    survey_id = TypeAdapter(SurveyId).validate_python(1)
    version_id = TypeAdapter(SurveyVersionId).validate_python(11)
    session_id = TypeAdapter(SubmissionSessionId).validate_python(uuid4())
    field_uuid = TypeAdapter(SurveyFieldUuid).validate_python(uuid4())
    version = SurveyVersion(survey_id=survey_id, version_number=1)
    version.id = version_id
    version.definition = SurveyDefinition.model_validate(
        {
            "id": "survey",
            "versionId": version_id,
            "revision": 1,
            "title": "Survey",
            "projectName": "Project",
            "status": "published",
            "document": {
                "sections": [
                    {
                        "id": "section",
                        "title": "Section",
                        "blocks": [
                            {
                                "id": "age_block",
                                "type": "input",
                                "field": {
                                    "id": "age",
                                    "uuid": field_uuid,
                                    "prompt": "Age?",
                                    "interaction": {"kind": "number"},
                                    "answerSpec": {"type": "integer", "required": True},
                                },
                            }
                        ],
                    }
                ]
            },
        }
    )
    session = SubmissionSession(
        project_id=project_id,
        survey_id=survey_id,
        survey_version_id=version_id,
        response_store_id=TypeAdapter(ResponseStoreId).validate_python(1),
        browser_session_token_hash=b"token-hash",
        linkage_key_version=1,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    session.id = session_id
    session.survey_version = version
    ctx = SubmissionSessionContext(
        session_id=session_id,
        project_id=project_id,
        survey_id=survey_id,
        survey_version_id=version_id,
        envelope_id=uuid4(),
        session_locator=SessionLocator(b"s" * 32),
        linkage_key=LinkageKey(version=1, secret=b"k" * 32, aws_version_id="test"),
        linkage_key_version=1,
        _session_dek=PlaintextSessionKey(b"d" * 32),
        crypto_version=1,
        expires_at=session.expires_at,
        browser_session_token_hash=session.browser_session_token_hash,
    )
    slot = SubmissionAnswerSlot(
        submission_session_id=session_id, survey_version_id=version_id, field_uuid=field_uuid, field_id="age"
    )
    slot.id = uuid4()
    locked = Mock(return_value=session)
    monkeypatch.setattr(module.ssr, "lock_for_update", locked)
    monkeypatch.setattr(module.ssr, "get_by_id", Mock(return_value=session))
    slots = create_autospec(module.submission_answer_slots.get_or_create, return_value=slot)
    monkeypatch.setattr(module.submission_answer_slots, "get_or_create", slots)
    saved_at = datetime(2020, 1, 1, tzinfo=UTC)
    save = create_autospec(
        module.response_answer_repo.upsert_current, return_value=SimpleNamespace(updated_at=saved_at)
    )
    monkeypatch.setattr(module.response_answer_repo, "upsert_current", save)
    events = Mock()
    monkeypatch.setattr(module.event_repo, "record_event", events)
    commit = Mock()
    monkeypatch.setattr(module, "commit_with_err_handle", commit)
    return SimpleNamespace(
        db=Mock(spec=Session),
        response_db=Mock(spec=Session),
        ctx=ctx,
        session=session,
        field_uuid=field_uuid,
        slot=slot,
        slots=slots,
        save=save,
        events=events,
        commit=commit,
        locked=locked,
        saved_at=saved_at,
        service=module.AnswerSaveService(),
        mutation=TypeAdapter(ClientMutationId).validate_python(uuid4()),
    )


def save(setup, state="answered", **overrides):
    raw: dict[str, object] = {"state": state}
    if state == "answered":
        raw.update(answer_spec={"type": "integer", "required": True}, answer_value=24)
    args = {
        "ctx": setup.ctx,
        "field_uuid": setup.field_uuid,
        "answer": TypeAdapter(AnswerData).validate_python(raw),
        "client_mutation_id": setup.mutation,
    }
    args.update(overrides)
    return setup.service.save_answer(setup.db, setup.response_db, **args)


@pytest.mark.parametrize("state", ["answered", "cleared"])
def test_save_uses_server_field_and_persists_only_ciphertext(setup, state):
    result = save(setup, state)
    setup.slots.assert_called_once_with(
        setup.db,
        submission_session_id=setup.ctx.session_id,
        survey_version_id=setup.ctx.survey_version_id,
        field_uuid=setup.field_uuid,
        field_id="age",
    )
    assert result.field_uuid == setup.field_uuid and result.field_id == "age" and result.saved_at == setup.saved_at
    stored = setup.save.call_args.kwargs
    assert set(stored) == {"envelope_id", "answer_locator", "nonce", "ciphertext", "client_mutation_id"}
    assert [call.args[0] for call in setup.commit.call_args_list] == [setup.db, setup.response_db]
    context = AnswerContext(
        dek=setup.ctx.plaintext_session_dek,
        crypto_version=1,
        envelope_id=setup.ctx.envelope_id,
        answer_locator=stored["answer_locator"],
    )
    decrypted = decrypt_answer_current(ciphertext=stored["ciphertext"], nonce=stored["nonce"], context=context)
    assert decrypted.state == state and decrypted.field_uuid == setup.field_uuid
    if decrypted.state == "answered":
        assert decrypted.answer_spec.type == "integer" and decrypted.answer_value == 24
    setup.events.assert_called_once_with(
        setup.db,
        session_id=setup.ctx.session_id,
        survey_version_id=setup.ctx.survey_version_id,
        event_type="answer_saved",
        field_uuid=setup.field_uuid,
        log_label="answer_save.analytics",
    )


def test_answer_and_clear_keep_the_same_slot_locator(setup):
    save(setup)
    first = setup.save.call_args.kwargs
    save(setup, "cleared")
    second = setup.save.call_args.kwargs
    assert first["answer_locator"] == second["answer_locator"]
    assert first["nonce"] != second["nonce"]


@pytest.mark.parametrize("state", ["completed", "abandoned"])
def test_non_active_session_does_not_create_slot_or_write(setup, state):
    setup.session.session_status = state
    with pytest.raises(SessionInvalidError):
        save(setup)
    setup.slots.assert_not_called()
    setup.save.assert_not_called()
    setup.commit.assert_not_called()


def test_missing_session_is_rejected_before_slot_creation(setup):
    setup.locked.return_value = None
    with pytest.raises(AnswerSaveError):
        save(setup)
    setup.slots.assert_not_called()


def test_unknown_field_is_rejected_against_pinned_document(setup):
    with pytest.raises(FieldNotInVersionError):
        save(setup, field_uuid=TypeAdapter(SurveyFieldUuid).validate_python(uuid4()))
    setup.slots.assert_not_called()
    setup.save.assert_not_called()


def test_stale_cached_version_cannot_bind_a_slot(setup):
    changed = replace(setup.ctx, survey_version_id=TypeAdapter(SurveyVersionId).validate_python(99))
    with pytest.raises(SessionInvalidError):
        save(setup, ctx=changed)
    setup.slots.assert_not_called()


def test_duplicate_field_identity_is_not_resolved_arbitrarily(setup):
    definition = setup.session.survey_version.definition
    assert definition is not None
    section = definition.document.sections[0]
    section.blocks.append(section.blocks[0].model_copy(deep=True))
    with pytest.raises(FieldNotInVersionError):
        save(setup)
    setup.slots.assert_not_called()


def test_field_view_event_uses_the_same_pinned_field_lookup(setup):
    setup.service.record_field_viewed(setup.db, ctx=setup.ctx, field_uuid=setup.field_uuid)
    assert setup.events.call_args.kwargs["event_type"] == "field_viewed"
    assert setup.events.call_args.kwargs["field_uuid"] == setup.field_uuid
    setup.slots.assert_not_called()
    setup.save.assert_not_called()
