"""Integration tests for document-field answer saves and field-viewed events."""

from __future__ import annotations

import os
import uuid
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from app.crypto.answers import derive_slot_answer_locator
from app.crypto.locators import derive_session_locator
from app.crypto.models import LinkageKey, PlaintextSessionKey, SubmissionSessionContext
from app.domain.errors import FieldNotInDefinitionError, InvalidFieldAnswerError
from app.repositories.response import response_envelope_repo
from app.schema.orm.core import SubmissionAnswerSlot, SubmissionEvent
from app.schema.orm.core.project import Project
from app.schema.orm.core.response_store import ResponseStore
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.user import User
from app.schema.orm.response import ResponseAnswer
from app.services.public_submissions.core.actions.answer_save import AnswerSaveService

if TYPE_CHECKING:
    from tests.conftest import DbSessions

_FIELD_ID = "field_health"
_LINKAGE_SECRET = b"\xcc" * 32
_FAKE_LINKAGE_KEY = LinkageKey(version=1, secret=_LINKAGE_SECRET, aws_version_id="test-version")
_FAKE_PLAINTEXT_DEK = PlaintextSessionKey(os.urandom(32))
_ANSWER_SAVE_MODULE = "app.services.public_submissions.core.actions.answer_save"


def _definition() -> dict[str, object]:
    return {
        "document": {
            "sections": [
                {
                    "id": "section_main",
                    "title": "Main",
                    "blocks": [
                        {
                            "id": "block_health",
                            "type": "input",
                            "field": {
                                "id": _FIELD_ID,
                                "key": "health",
                                "prompt": "How is your health?",
                                "interaction": {"kind": "text"},
                                "response": {
                                    "type": "string",
                                    "validation": {"min_length": 2, "max_length": 40},
                                },
                            },
                        }
                    ],
                }
            ]
        }
    }


def _setup_core_fixtures(core_db):
    user = User(auth0_user_id="auth0|answer-save", email="answer-save@example.com", display_name="Answer Save")
    core_db.add(user)
    core_db.flush()

    project = Project(name="Answer project", slug=f"answer-project-{uuid.uuid4().hex[:8]}", created_by_user_id=user.id)
    core_db.add(project)
    core_db.flush()

    store = ResponseStore(
        project_id=project.id,
        name="main-store",
        store_type="platform_postgres",
        connection_reference={"kind": "postgres"},
        created_by_user_id=user.id,
    )
    core_db.add(store)
    core_db.flush()

    survey = Survey(
        project_id=project.id,
        title="Health survey",
        default_response_store_id=store.id,
        created_by_user_id=user.id,
    )
    core_db.add(survey)
    core_db.flush()

    version = SurveyVersion(
        survey_id=survey.id,
        version_number=1,
        revision=0,
        status="draft",
        definition=_definition(),
        created_by_user_id=user.id,
    )
    core_db.add(version)
    core_db.flush()
    return project, survey, version


def _create_session_row(core_db, project, survey, version):
    from app.repositories.core.submission_sessions import create_session

    raw_token = "test-token-" + uuid.uuid4().hex[:8]
    session = create_session(
        core_db,
        project_id=project.id,
        survey_id=survey.id,
        survey_version_id=version.id,
        response_store_id=survey.default_response_store_id,
        link_id=None,
        project_subject_id=None,
        raw_browser_session_token=raw_token,
        linkage_key_version=1,
    )
    return session


def _create_envelope_and_context(response_db, session, version):
    session_locator = derive_session_locator(session.id, _FAKE_LINKAGE_KEY).session_locator
    envelope = response_envelope_repo.create(
        response_db,
        session_locator=session_locator,
        linkage_key_version=1,
        wrapped_session_dek=os.urandom(64),
        crypto_version=1,
    )
    return SubmissionSessionContext(
        session_id=session.id,
        project_id=session.project_id,
        survey_id=session.survey_id,
        survey_version_id=version.id,
        envelope_id=envelope.id,
        session_locator=session_locator,
        linkage_key=_FAKE_LINKAGE_KEY,
        linkage_key_version=_FAKE_LINKAGE_KEY.version,
        _session_dek=_FAKE_PLAINTEXT_DEK,
        crypto_version=1,
        expires_at=session.expires_at,
        browser_session_token_hash=session.browser_session_token_hash,
    )


def _setup(db_sessions: DbSessions):
    core_db = db_sessions.core
    response_db = db_sessions.response
    project, survey, version = _setup_core_fixtures(core_db)
    session = _create_session_row(core_db, project, survey, version)
    ctx = _create_envelope_and_context(response_db, session, version)
    return core_db, response_db, session, ctx


class TestAnswerSave:
    def test_save_answer_resolves_field_and_returns_typed_result(self, db_sessions: DbSessions) -> None:
        core_db, response_db, _session, ctx = _setup(db_sessions)

        result = AnswerSaveService().save_answer(
            core_db,
            response_db,
            ctx=ctx,
            field_id=_FIELD_ID,
            answer_state="answered",
            answer_value="healthy",
            client_mutation_id=uuid.uuid4(),
        )

        assert result.field_key == "health"
        assert result.response_type == "string"
        assert result.value == "healthy"

    def test_mutation_id_dedup_returns_existing(self, db_sessions: DbSessions) -> None:
        core_db, response_db, _session, ctx = _setup(db_sessions)
        mutation_id = uuid.uuid4()
        service = AnswerSaveService()

        first = service.save_answer(
            core_db,
            response_db,
            ctx=ctx,
            field_id=_FIELD_ID,
            answer_state="answered",
            answer_value="healthy",
            client_mutation_id=mutation_id,
        )
        second = service.save_answer(
            core_db,
            response_db,
            ctx=ctx,
            field_id=_FIELD_ID,
            answer_state="answered",
            answer_value="healthy",
            client_mutation_id=mutation_id,
        )

        assert first == second

    def test_analytics_rollback_does_not_orphan_response_answer(
        self,
        db_sessions: DbSessions,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        core_db, response_db, session, ctx = _setup(db_sessions)

        def _analytics_failure_rollback(db, **_kwargs) -> None:
            db.rollback()

        monkeypatch.setattr(f"{_ANSWER_SAVE_MODULE}.event_repo.record_event", _analytics_failure_rollback)
        service = AnswerSaveService()
        service.save_answer(
            core_db,
            response_db,
            ctx=ctx,
            field_id=_FIELD_ID,
            answer_state="answered",
            answer_value="healthy",
            client_mutation_id=uuid.uuid4(),
        )

        slot = core_db.scalar(
            select(SubmissionAnswerSlot).where(
                SubmissionAnswerSlot.submission_session_id == session.id,
                SubmissionAnswerSlot.field_id == _FIELD_ID,
            )
        )
        assert slot is not None
        answer_locator = derive_slot_answer_locator(slot.id, ctx.linkage_key)
        assert response_db.get(ResponseAnswer, answer_locator) is not None

    def test_unknown_field_raises(self, db_sessions: DbSessions) -> None:
        core_db, response_db, _session, ctx = _setup(db_sessions)

        with pytest.raises(FieldNotInDefinitionError):
            AnswerSaveService().save_answer(
                core_db,
                response_db,
                ctx=ctx,
                field_id="field_missing",
                answer_state="answered",
                answer_value="healthy",
                client_mutation_id=uuid.uuid4(),
            )

    def test_answer_is_validated_against_resolved_field(self, db_sessions: DbSessions) -> None:
        core_db, response_db, _session, ctx = _setup(db_sessions)

        with pytest.raises(InvalidFieldAnswerError, match="shorter"):
            AnswerSaveService().save_answer(
                core_db,
                response_db,
                ctx=ctx,
                field_id=_FIELD_ID,
                answer_state="answered",
                answer_value="x",
                client_mutation_id=uuid.uuid4(),
            )


class TestFieldViewed:
    def test_record_field_viewed_resolves_and_records_field(self, db_sessions: DbSessions) -> None:
        core_db, _response_db, session, ctx = _setup(db_sessions)

        AnswerSaveService().record_field_viewed(core_db, ctx=ctx, field_id=_FIELD_ID)

        event = core_db.scalar(
            select(SubmissionEvent).where(
                SubmissionEvent.session_id == session.id,
                SubmissionEvent.event_type == "field_viewed",
            )
        )
        assert event is not None
        assert event.field_id == _FIELD_ID

    def test_record_field_viewed_rejects_unknown_field(self, db_sessions: DbSessions) -> None:
        core_db, _response_db, _session, ctx = _setup(db_sessions)

        with pytest.raises(FieldNotInDefinitionError):
            AnswerSaveService().record_field_viewed(core_db, ctx=ctx, field_id="field_missing")
