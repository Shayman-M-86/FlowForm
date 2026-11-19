"""Persist answers by pinned document field identity across both databases."""

import os
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from pydantic import TypeAdapter

from app.crypto.answers import decrypt_answer_current, derive_slot_answer_locator
from app.crypto.locators import derive_session_locator
from app.crypto.models import AnswerContext, LinkageKey, PlaintextSessionKey
from app.domain.errors import FieldNotInVersionError, SessionInvalidError
from app.repositories.core import submission_answer_slots, submission_events, submission_sessions
from app.repositories.response import response_answer_repo, response_envelope_repo
from app.schema.models.survey_document import SurveyDefinition
from app.schema.models.survey_document.answers import AnswerData
from app.schema.orm.core.project import Project
from app.schema.orm.core.response_store import ResponseStore
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.types import ClientMutationId, SurveyFieldUuid, WrappedSessionKey
from app.services.public_submissions.core.actions.answer_save import AnswerSaveService

if TYPE_CHECKING:
    from tests.conftest import DbSessions

_LINKAGE = LinkageKey(version=1, secret=b"k" * 32, aws_version_id="test-version")
_DEK = PlaintextSessionKey(b"d" * 32)
_ANSWER = TypeAdapter(AnswerData)


def setup(db_sessions):
    from app.crypto.models import SubmissionSessionContext

    core_db, response_db = db_sessions.core, db_sessions.response
    project = Project(name="Field answers", slug=f"answers-{uuid4().hex}")
    core_db.add(project)
    core_db.flush()
    store = ResponseStore(
        project_id=project.id,
        name="Responses",
        store_type="platform_postgres",
        connection_reference={"driver": "postgres", "database": "response"},
    )
    core_db.add(store)
    core_db.flush()
    survey = Survey(project_id=project.id, title="Survey", default_response_store_id=store.id)
    core_db.add(survey)
    core_db.flush()
    version = SurveyVersion(survey_id=survey.id, version_number=1)
    core_db.add(version)
    core_db.flush()
    field_uuid = TypeAdapter(SurveyFieldUuid).validate_python(uuid4())
    version.definition = SurveyDefinition.model_validate(
        {
            "id": "survey",
            "versionId": version.id,
            "revision": 1,
            "title": "Survey",
            "projectName": "Field answers",
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
    version.status = "published"
    core_db.flush()
    session = submission_sessions.create_session(
        core_db,
        project_id=project.id,
        survey_id=survey.id,
        survey_version_id=version.id,
        response_store_id=store.id,
        link_id=None,
        project_subject_id=None,
        raw_browser_session_token=uuid4().hex,
        linkage_key_version=1,
    )
    locator = derive_session_locator(session.id, _LINKAGE).session_locator
    envelope = response_envelope_repo.create(
        response_db,
        session_locator=locator,
        linkage_key_version=1,
        wrapped_session_dek=WrappedSessionKey(os.urandom(64)),
        crypto_version=1,
    )
    ctx = SubmissionSessionContext(
        session_id=session.id,
        project_id=project.id,
        survey_id=survey.id,
        survey_version_id=version.id,
        envelope_id=envelope.id,
        session_locator=locator,
        linkage_key=_LINKAGE,
        linkage_key_version=1,
        _session_dek=_DEK,
        crypto_version=1,
        expires_at=session.expires_at,
        browser_session_token_hash=session.browser_session_token_hash,
    )
    return session, ctx, field_uuid


def save(db_sessions, ctx, field_uuid, answer):
    return AnswerSaveService().save_answer(
        db_sessions.core,
        db_sessions.response,
        ctx=ctx,
        field_uuid=field_uuid,
        answer=answer,
        client_mutation_id=TypeAdapter(ClientMutationId).validate_python(uuid4()),
    )


def test_answer_save_and_clear_reuse_one_field_slot(db_sessions: DbSessions):
    _, ctx, field_uuid = setup(db_sessions)
    answered = _ANSWER.validate_python(
        {"state": "answered", "answer_spec": {"type": "integer", "required": True}, "answer_value": 24}
    )
    result = save(db_sessions, ctx, field_uuid, answered)
    slots = submission_answer_slots.list_by_session(db_sessions.core, submission_session_id=ctx.session_id)
    assert len(slots) == 1 and slots[0].field_uuid == field_uuid and slots[0].field_id == "age"
    locator = derive_slot_answer_locator(slots[0].id, _LINKAGE)
    stored = response_answer_repo.get_by_locator(db_sessions.response, locator)
    assert stored is not None and stored.updated_at == result.saved_at
    crypto = AnswerContext(dek=_DEK, crypto_version=1, envelope_id=ctx.envelope_id, answer_locator=locator)
    payload = decrypt_answer_current(ciphertext=stored.ciphertext, nonce=stored.nonce, context=crypto)
    assert payload.state == "answered" and payload.answer_spec.type == "integer" and payload.answer_value == 24
    save(db_sessions, ctx, field_uuid, _ANSWER.validate_python({"state": "cleared"}))
    assert len(submission_answer_slots.list_by_session(db_sessions.core, submission_session_id=ctx.session_id)) == 1
    db_sessions.response.expire_all()
    cleared = response_answer_repo.get_by_locator(db_sessions.response, locator)
    assert cleared is not None
    assert decrypt_answer_current(ciphertext=cleared.ciphertext, nonce=cleared.nonce, context=crypto).state == "cleared"


def test_field_must_belong_to_the_pinned_definition(db_sessions: DbSessions):
    _, ctx, _ = setup(db_sessions)
    with pytest.raises(FieldNotInVersionError):
        save(
            db_sessions,
            ctx,
            TypeAdapter(SurveyFieldUuid).validate_python(uuid4()),
            _ANSWER.validate_python({"state": "cleared"}),
        )
    assert submission_answer_slots.list_by_session(db_sessions.core, submission_session_id=ctx.session_id) == []


def test_completed_session_cannot_save(db_sessions: DbSessions):
    session, ctx, field_uuid = setup(db_sessions)
    session.session_status = "completed"
    db_sessions.core.flush()
    with pytest.raises(SessionInvalidError):
        save(db_sessions, ctx, field_uuid, _ANSWER.validate_python({"state": "cleared"}))


def test_field_view_event_uses_field_identity(db_sessions: DbSessions):
    _, ctx, field_uuid = setup(db_sessions)
    AnswerSaveService().record_field_viewed(db_sessions.core, ctx=ctx, field_uuid=field_uuid)
    events = submission_events.list_by_session(db_sessions.core, session_id=ctx.session_id)
    assert len(events) == 1 and events[0].event_type == "field_viewed" and events[0].field_uuid == field_uuid
